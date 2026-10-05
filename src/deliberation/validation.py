"""Validate protocol consistency and reference existence, never persuasiveness."""

from .schemas import Critique, Decision, Proposal


def unique(values, label):
    if len(values) != len(set(values)):
        raise ValueError(f"Duplicate {label}")


def challenge_contract(dialogue):
    previous = next((d for d in reversed(dialogue) if d["role"] == "critic"), None)
    active = previous["content"]["challenges"] if previous else []
    return {
        "latest_critic_message": previous["message_id"] if previous else None,
        "active_ids": [c["id"] for c in active],
        "required_proposer_response_ids": [c["id"] for c in active if c["blocks_agreement"]],
        "optional_proposer_response_ids": [c["id"] for c in active if not c["blocks_agreement"]],
        "required_critic_assessment_ids": [c["id"] for c in active],
        "rule": "Respond/assess only these active IDs, not IDs resolved in older turns. "
        "Unresolved challenges retain the same ID; new challenges need new IDs.",
    }


def validate_turn(role, message, dialogue):
    contract = challenge_contract(dialogue)
    outstanding = set(contract["active_ids"])
    errors = []
    if role == "proposer":
        assert isinstance(message, Proposal)
        ids = [r.challenge_id for r in message.responses]
        unique(ids, "challenge response IDs")
        unique([a.id for a in message.assumptions], "assumption IDs")
        missing = set(contract["required_proposer_response_ids"]) - set(ids)
        unexpected = set(ids) - outstanding
        if missing or unexpected:
            raise ValueError(
                f"Responses must cover outstanding material challenges. Missing IDs: {sorted(missing)}; "
                f"unexpected/resolved IDs to remove: {sorted(unexpected)}; "
                f"allowed active IDs: {sorted(outstanding)}."
            )
        return
    assert isinstance(message, Critique)
    ids = [c.id for c in message.challenges]
    unique(ids, "challenge IDs")
    assessed = [a.challenge_id for a in message.response_assessments]
    unique(assessed, "assessment IDs")
    if set(assessed) != outstanding:
        errors.append(
            f"response_assessments must use exactly {sorted(outstanding)}. "
            f"Missing: {sorted(outstanding - set(assessed))}; "
            f"unexpected: {sorted(set(assessed) - outstanding)}."
        )
    for item in message.response_assessments:
        if (item.disposition == "unresolved") != (item.challenge_id in ids):
            errors.append(
                f"{item.challenge_id} is {item.disposition}: "
                + (
                    "keep this SAME ID in challenges, not a renamed replacement."
                    if item.disposition == "unresolved"
                    else "remove it from challenges; use a fresh ID if there is a new issue."
                )
            )
    blockers = any(c.blocks_agreement for c in message.challenges)
    if message.assessment == "complete" and blockers:
        errors.append("complete contradicts an outstanding challenge marked blocks_agreement.")
    if message.assessment == "stalled" and not blockers:
        errors.append("stalled requires an unresolved substantive blocker to agreement.")
    if message.assessment == "continue" and not message.next_exchange.strip():
        errors.append("continue requires a concrete next_exchange.")
    if errors:
        raise ValueError(" ".join(errors))


def validate_decision(decision: Decision, dialogue):
    messages = {d["message_id"]: d for d in dialogue}
    fields = (
        "agreed_included_scope",
        "agreed_excluded_scope",
        "conditional_scope",
        "disputed_scope",
        "unresolved_scope",
        "assumptions",
        "success_criteria",
        "open_human_questions",
        "rejected_options",
    )
    errors = []
    for field in fields:
        for index, item in enumerate(getattr(decision, field)):
            location = f"{field}[{index}].supporting_messages"
            refs = item.supporting_messages
            if len(refs) != len(set(refs)):
                errors.append(f"{location}: duplicate references.")
            unknown = set(refs) - messages.keys()
            if unknown:
                errors.append(f"{location}: Unknown supporting_messages: {sorted(unknown)}.")
                continue
            agreed = field.startswith("agreed_") or getattr(item, "disposition", None) in (
                "agreed",
                "accepted",
            )
            if agreed and {messages[r]["role"] for r in refs} != {"proposer", "critic"}:
                errors.append(
                    f"{location}: Agreement requires cited Proposer and Critic messages; got {refs}. "
                    "Cite actual support from both, or move the item to an unresolved/proposed category."
                )
    last = next((d for d in reversed(dialogue) if d["role"] == "critic"), None)
    if (
        last
        and any(c["blocks_agreement"] for c in last["content"]["challenges"])
        and not decision.disputed_scope
        and not decision.unresolved_scope
    ):
        errors.append(
            "An outstanding agreement blocker requires explicit disputed_scope or unresolved_scope."
        )
    if errors:
        raise ValueError(" ".join(errors))
