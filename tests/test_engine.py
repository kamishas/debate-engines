"""Synthetic fixtures only. These tests do not establish model reasoning quality."""

import json

import pytest
from pydantic import ValidationError

from deliberation.cli import main
from deliberation.engine import Engine, RunError, Settings
from deliberation.logging import RunLog
from deliberation.provider import ProviderError, Reply
from deliberation.schemas import Confidence, Critique, Decision, FinalDocument, Proposal

CONF = {
    "score": 72,
    "justification": "Synthetic fixture; bounded scope.",
    "main_uncertainty": "The human owner has not verified the condition.",
}
CHALLENGE = {
    "id": "C1",
    "target": "visibility",
    "concern": "Restricted records might leak.",
    "resolution_needed": "Specify access boundaries.",
    "blocks_agreement": True,
}


def proposal(respond=False):
    return {
        "interpretation": "Synthetic: find a designated country contact.",
        "supplied_facts": ["Contact information is sensitive."],
        "included_scope": ["Show an explicitly designated contact where authorized."],
        "excluded_scope": ["Automatic ranking."],
        "conditional_scope": ["Enable access after the owner confirms permissions."],
        "assumptions": [
            {
                "id": "A1",
                "statement": "An existing designation can be used.",
                "rationale": "Proposed starting assumption, not a supplied fact.",
            }
        ],
        "success_criteria": ["An unauthorized user cannot view a restricted contact."],
        "responses": (
            [
                {
                    "challenge_id": "C1",
                    "action": "revise",
                    "rationale": "Updated scope explicitly respects authorization.",
                }
            ]
            if respond
            else []
        ),
        "open_questions": [
            {
                "question": "Who owns authorization?",
                "impact": "Access is conditional.",
                "blocks_implementation": True,
            }
        ],
        "confidence": CONF,
    }


def critique(assessment="continue", *, prior=False, blocker=True):
    return {
        "response_assessments": (
            [
                {
                    "challenge_id": "C1",
                    "disposition": "unresolved" if blocker else "resolved",
                    "reason": "Synthetic assessment of response.",
                }
            ]
            if prior
            else []
        ),
        "accepted_points": ["Automatic ranking is excluded."],
        "challenges": [CHALLENGE] if blocker else [],
        "open_questions": [],
        "assessment": assessment,
        "assessment_reason": "Synthetic: bounded conditions are documented."
        if not blocker
        else "Synthetic: authorization remains disputed; more evidence is needed.",
        "next_exchange": "Resolve visibility boundaries." if assessment == "continue" else "",
        "confidence": CONF,
    }


def decision(*, disputed=False):
    evidence = {
        "statement": "Automatic ranking is excluded.",
        "reason": "The Proposer excluded it and the Critic explicitly accepted that.",
        "supporting_messages": ["r1-proposer", "r1-critic"],
    }
    return {
        "summary": "SYNTHETIC FIXTURE: a conditional decision, not a real model run.",
        "agreed_included_scope": [],
        "agreed_excluded_scope": [evidence],
        "conditional_scope": [],
        "disputed_scope": (
            [{**evidence, "statement": "Authorization remains disputed."}] if disputed else []
        ),
        "unresolved_scope": [],
        "assumptions": [],
        "success_criteria": [],
        "open_human_questions": [],
        "rejected_options": [],
    }


class Scripted:
    def __init__(self, responses, inspect=None):
        self.responses = iter(responses)
        self.calls = []
        self.inspect = inspect

    def generate(self, **kwargs):
        if self.inspect:
            self.inspect(len(self.calls))
        self.calls.append(kwargs)
        response = next(self.responses)
        if isinstance(response, Exception):
            raise response
        if isinstance(response, Reply):
            return response
        return Reply(
            response if isinstance(response, str) else json.dumps(response),
            input_tokens=10,
            output_tokens=20,
        )


def completed():
    return [
        proposal(),
        critique(),
        proposal(True),
        critique("complete", prior=True, blocker=False),
        decision(),
    ]


def run(tmp_path, responses=None, **settings):
    provider = Scripted(responses if responses is not None else completed())
    engine = Engine(provider, Settings(max_rounds=2, **settings), sleeper=lambda _: None)
    path, meta = engine.run("Synthetic request", "Synthetic context", tmp_path)
    return provider, path, meta


def events(path):
    return [json.loads(line) for line in (path / "exchanges.jsonl").read_text().splitlines()]


def test_complete_on_final_round_preserves_completed_and_bonus_fields(tmp_path):
    provider, path, meta = run(tmp_path)
    final = FinalDocument.model_validate_json((path / "final.json").read_text())
    assert meta["outcome"] == "completed"
    assert meta["completed_rounds"] == 2
    assert meta["report_status"] == "succeeded"
    assert not final.partial
    assert final.latest_confidence["proposer"].round == 2
    assert final.latest_confidence["critic"].score == CONF["score"]
    assert provider.calls[-1]["schema"] is Decision
    assert [call["schema"] for call in provider.calls] == [
        Proposal,
        Critique,
        Proposal,
        Critique,
        Decision,
    ]
    kinds = [e["event"] for e in events(path)]
    stopped = kinds.index("deliberation_stopped")
    summary_call = next(
        i
        for i, e in enumerate(events(path))
        if e["event"] == "call_started" and e["role"] == "summarizer"
    )
    assert stopped < summary_call


def test_round_one_completion_is_deferred(tmp_path):
    responses = [
        proposal(),
        critique("complete", blocker=False),
        proposal(),
        critique("complete", blocker=False),
        decision(),
    ]
    _, path, meta = run(tmp_path, responses)
    assert meta["completed_rounds"] == 2
    assert any(e["event"] == "termination_deferred" for e in events(path))


@pytest.mark.parametrize("cap", [-1, 0, 1, 21])
def test_invalid_caps(cap):
    with pytest.raises(ValueError, match="max_rounds"):
        Settings(max_rounds=cap)


def test_cap_does_not_imply_agreement(tmp_path):
    _, path, meta = run(
        tmp_path,
        [proposal(), critique(), proposal(True), critique(prior=True), decision(disputed=True)],
    )
    final = json.loads((path / "final.json").read_text())
    assert meta["outcome"] == "capped"
    assert final["partial"]
    assert final["decision"]["disputed_scope"]
    assert final["decision"]["agreed_included_scope"] == []


def test_stall_retains_outstanding_disagreement_and_wins_over_cap(tmp_path):
    _, path, meta = run(
        tmp_path,
        [
            proposal(),
            critique("stalled"),
            proposal(True),
            critique("stalled", prior=True),
            decision(disputed=True),
        ],
    )
    assert meta["completed_rounds"] == 2
    assert meta["outcome"] == "stalled"
    assert json.loads((path / "final.json").read_text())["decision"]["disputed_scope"]


def test_structural_completion_contradiction_is_repaired(tmp_path):
    responses = completed()
    responses.insert(3, critique("complete", prior=True))
    _, path, meta = run(tmp_path, responses)
    assert meta["outcome"] == "completed"
    assert meta["provider_calls"] == 6
    assert sum(e["event"] == "validation_failed" for e in events(path)) == 1


@pytest.mark.parametrize("invalid_attempts", [1, 2])
def test_malformed_output_repair_is_logged_and_does_not_add_round(tmp_path, invalid_attempts):
    provider = Scripted(["bad JSON"] * invalid_attempts + completed())
    path, meta = Engine(provider, Settings(), sleeper=lambda _: None).run(
        "Synthetic request", "Synthetic context", tmp_path
    )
    assert meta["outcome"] == "completed"
    assert meta["completed_rounds"] == 2
    assert meta["provider_calls"] == 5 + invalid_attempts
    assert any(e.get("text") == "bad JSON" for e in events(path))
    assert json.loads(provider.calls[1]["content"])["round"] == 1
    assert "repair" in json.loads(provider.calls[1]["content"])


def test_exhausted_malformed_output_fails_without_fake_final(tmp_path):
    _, path, meta = run(tmp_path, ["bad", "still bad"], repair_attempts=1)
    assert meta["outcome"] == "error"
    assert meta["report_status"] == "skipped"
    assert not (path / "final.json").exists()
    assert meta["provider_calls"] == 2


def test_exhausted_provider_retries_are_error(tmp_path):
    failure = ProviderError("Temporary failure", transient=True)
    _, path, meta = run(tmp_path, [failure, failure])
    assert meta["outcome"] == "error"
    assert meta["provider_calls"] == 2
    assert sum(e["event"] == "provider_error" for e in events(path)) == 2


def test_transient_retry_succeeds_with_same_turn(tmp_path):
    provider, _, meta = run(tmp_path, [ProviderError("Try again", transient=True)] + completed())
    assert meta["outcome"] == "completed"
    assert provider.calls[0]["content"] == provider.calls[1]["content"]


def test_nontransient_provider_error_is_not_retried(tmp_path):
    _, _, meta = run(tmp_path, [ProviderError("Context limit reached")])
    assert meta["outcome"] == "error"
    assert meta["provider_calls"] == 1


@pytest.mark.parametrize("score", [-1, 101, 1.1, "80", True])
def test_confidence_rejects_invalid_score(score):
    with pytest.raises(ValidationError):
        Confidence.model_validate({**CONF, "score": score})


@pytest.mark.parametrize("score", [0, 50, 100])
def test_confidence_accepts_range(score):
    assert Confidence.model_validate({**CONF, "score": score}).score == score


def test_exchanges_exist_before_next_call(tmp_path):
    def inspect(index):
        if index:
            paths = list(tmp_path.glob("*/exchanges.jsonl"))
            logged = [json.loads(line) for line in paths[0].read_text().splitlines()]
            assert sum(e["event"] == "exchange" for e in logged) == min(index, 4)
            metadata = json.loads((paths[0].parent / "metadata.json").read_text())
            assert metadata["completed_rounds"] == min(index // 2, 2)

    provider = Scripted(completed(), inspect)
    Engine(provider, Settings(max_rounds=2)).run("Synthetic", "Context", tmp_path)


def test_summarizer_failure_preserves_outcome_and_transcript(tmp_path):
    _, path, meta = run(tmp_path, completed()[:-1] + [ProviderError("Summary unavailable")])
    assert meta["outcome"] == "completed"
    assert meta["report_status"] == "failed"
    assert sum(e["event"] == "exchange" for e in events(path)) == 4
    assert not (path / "final.json").exists()


def test_summarizer_receives_full_dialogue_and_role_specific_payload(tmp_path):
    provider, path, meta = run(tmp_path)
    payload = json.loads(provider.calls[-1]["content"])
    for field in ("round", "protocol_feedback", "challenge_contract"):
        assert field not in payload
        assert field in json.loads(provider.calls[0]["content"])
    assert "message_index" not in json.loads(provider.calls[0]["content"])
    accepted = [e for e in events(path) if e["event"] == "exchange"]
    assert payload["dialogue"] == [
        {key: e[key] for key in ("message_id", "role", "round", "content")} for e in accepted
    ]
    assert payload["message_index"] == [
        {key: e[key] for key in ("message_id", "role", "round")} for e in accepted
    ]
    assert payload["original_request"] == "Synthetic request"
    assert payload["system_context"] == "Synthetic context"
    assert payload["termination"] == {
        "outcome": meta["outcome"],
        "reason": meta["termination_reason"],
        "completed_rounds": 2,
    }


@pytest.mark.parametrize("outcome", ["capped", "error"])
def test_summarizer_receives_actual_stop_facts_without_rejected_turns(tmp_path, outcome):
    invalid = critique(prior=True)
    invalid["response_assessments"][0]["disposition"] = "resolved"
    ending = [invalid, invalid] if outcome == "error" else [critique(prior=True)]
    provider, path, meta = run(
        tmp_path,
        [proposal(), critique(), proposal(True), *ending, decision(disputed=True)],
        repair_attempts=1,
    )
    assert meta["outcome"] == outcome
    assert meta["report_status"] == "succeeded"
    payload = json.loads(provider.calls[-1]["content"])
    assert payload["termination"] == {
        "outcome": outcome,
        "reason": meta["termination_reason"],
        "completed_rounds": 1 if outcome == "error" else 2,
    }
    if outcome == "error":
        assert "C1 is resolved" in payload["termination"]["reason"]
        assert [e["message_id"] for e in payload["message_index"]] == [
            "r1-proposer",
            "r1-critic",
            "r2-proposer",
        ]
        assert payload["dialogue"][-1]["role"] == "proposer"
    assert "protocol_feedback" not in payload
    assert "round" not in payload
    final = json.loads((path / "final.json").read_text())
    assert final["termination_reason"] == meta["termination_reason"]
    assert final["outcome"] == outcome and final["partial"]


@pytest.mark.parametrize("category", ["disputed_scope", "unresolved_scope"])
def test_outstanding_report_concerns_allow_disputed_or_unresolved_scope(tmp_path, category):
    report = decision()
    report[category] = [
        {
            "statement": "Authorization remains an outstanding concern.",
            "reason": "The latest Critic retains C1 as a blocker.",
            "supporting_messages": ["r2-critic"],
        }
    ]
    _, path, meta = run(
        tmp_path, [proposal(), critique(), proposal(True), critique(prior=True), report]
    )
    assert meta["outcome"] == "capped" and meta["report_status"] == "succeeded"
    assert json.loads((path / "final.json").read_text())["decision"][category]


def test_outstanding_report_concerns_cannot_be_omitted(tmp_path):
    _, path, meta = run(
        tmp_path,
        [proposal(), critique(), proposal(True), critique(prior=True), decision(), decision()],
        repair_attempts=1,
    )
    assert meta["report_status"] == "failed"
    assert "disputed_scope or unresolved_scope" in meta["report_error"]
    assert not (path / "final.json").exists()


@pytest.mark.parametrize("disposition", ["agreed", "proposed"])
def test_criterion_without_critic_evidence_must_remain_proposed(tmp_path, disposition):
    report = decision()
    report["success_criteria"] = [
        {
            "statement": "Synthetic proposed criterion.",
            "reason": "The cited message is only the Proposer's proposal.",
            "supporting_messages": ["r2-proposer"],
            "disposition": disposition,
        }
    ]
    _, _, meta = run(tmp_path, completed()[:-1] + [report, report], repair_attempts=1)
    assert meta["report_status"] == ("succeeded" if disposition == "proposed" else "failed")


def test_invalid_summary_references_detected_and_repaired(tmp_path):
    invalid = decision()
    invalid["agreed_excluded_scope"][0]["supporting_messages"] = ["r99-critic"]
    _, path, meta = run(tmp_path, completed()[:-1] + [invalid, decision()])
    assert meta["report_status"] == "succeeded"
    assert any("Unknown supporting" in e.get("error", "") for e in events(path))


def test_agreement_requires_both_roles(tmp_path):
    invalid = decision()
    invalid["agreed_excluded_scope"][0]["supporting_messages"] = ["r1-proposer"]
    _, _, meta = run(tmp_path, completed()[:-1] + [invalid, invalid], repair_attempts=1)
    assert meta["outcome"] == "completed"
    assert meta["report_status"] == "failed"


def test_missing_final_field_is_rejected(tmp_path):
    invalid = decision()
    del invalid["open_human_questions"]
    _, _, meta = run(tmp_path, completed()[:-1] + [invalid, invalid], repair_attempts=1)
    assert meta["report_status"] == "failed"


def test_error_with_partial_dialogue_can_produce_partial_report(tmp_path):
    partial = decision()
    partial["agreed_excluded_scope"] = []
    partial["unresolved_scope"] = [
        {
            "statement": "Designation is unreviewed.",
            "reason": "Critic did not respond.",
            "supporting_messages": ["r1-proposer"],
        }
    ]
    _, path, meta = run(tmp_path, [proposal(), ProviderError("Critic unavailable"), partial])
    final = json.loads((path / "final.json").read_text())
    assert meta["outcome"] == "error"
    assert final["partial"] and final["completed_rounds"] == 0
    assert set(final["latest_confidence"]) == {"proposer"}


def test_context_budget_fails_without_truncation(tmp_path):
    provider, _, meta = run(tmp_path, [], max_input_bytes=1024)
    assert meta["outcome"] == "error"
    assert provider.calls == []
    assert "not truncated" in meta["termination_reason"]


def test_call_budget_cannot_be_exceeded_even_by_summary(tmp_path):
    _, _, meta = run(tmp_path, completed()[:4], max_calls=4)
    assert meta["outcome"] == "completed"
    assert meta["report_status"] == "failed"
    assert meta["provider_calls"] == 4


def test_truncated_reply_is_saved_and_repaired(tmp_path):
    _, path, meta = run(tmp_path, [Reply('{"broken":', stop_reason="max_tokens")] + completed())
    assert meta["outcome"] == "completed"
    assert any(e.get("stop_reason") == "max_tokens" for e in events(path))


def test_write_failure_stops_calls_and_preserves_existing_transcript(tmp_path, monkeypatch):
    original = RunLog.write
    writes = 0

    def fail_after_exchange(self, name, data):
        nonlocal writes
        if name == "metadata.json":
            writes += 1
            if writes == 5:
                raise OSError("Synthetic full disk")
        original(self, name, data)

    monkeypatch.setattr(RunLog, "write", fail_after_exchange)
    provider = Scripted(completed())
    with pytest.raises(RunError, match="Output-writing"):
        Engine(provider, Settings()).run("Synthetic", "Context", tmp_path)
    assert len(provider.calls) == 1
    assert "exchange" in next(tmp_path.glob("*/exchanges.jsonl")).read_text()


def test_secrets_are_redacted_from_all_log_files(tmp_path, monkeypatch):
    secret = "sk-ant-test-DO-NOT-LOG"
    monkeypatch.setenv("ANTHROPIC_API_KEY", secret)
    logger = RunLog(tmp_path)
    logger.event("test", text=secret)
    logger.write("metadata.json", {"secret": secret})
    for file in logger.path.iterdir():
        assert secret not in file.read_text()


def test_request_data_and_peer_roles_remain_separate(tmp_path):
    provider, _, _ = run(tmp_path)
    payload = json.loads(provider.calls[2]["content"])
    assert [d["role"] for d in payload["dialogue"]] == ["proposer", "critic"]
    assert payload["dialogue"][1]["message_id"] == "r1-critic"
    assert payload["original_request"] == "Synthetic request"
    assert "Proposer" in provider.calls[2]["system"]
    assert "Critic" in provider.calls[3]["system"]


def test_missing_credentials_cli_is_actionable(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    context = tmp_path / "context.txt"
    context.write_text("Synthetic context")
    assert main(["--request", "Synthetic", "--context", str(context)]) == 1
    assert "Configure it locally" in capsys.readouterr().err


def test_invalid_input_cli_reports_error(tmp_path, capsys):
    assert main(["--request", "Synthetic", "--context", str(tmp_path / "missing")]) == 1
    assert "Error:" in capsys.readouterr().err


def test_unanswered_challenge_cannot_silently_disappear(tmp_path):
    _, _, meta = run(
        tmp_path,
        [proposal(), critique(), proposal(), proposal(), decision(disputed=True)],
        repair_attempts=1,
    )
    assert meta["outcome"] == "error"
    assert "outstanding material challenges" in meta["termination_reason"]


def test_optional_challenge_does_not_force_a_response():
    from deliberation.validation import validate_turn

    previous = critique()
    previous["challenges"][0] = {**previous["challenges"][0], "blocks_agreement": False}
    validate_turn(
        "proposer",
        Proposal.model_validate(proposal()),
        [{"message_id": "r1-critic", "role": "critic", "content": previous}],
    )


def test_challenge_contract_is_explicit_in_later_calls(tmp_path):
    provider, _, _ = run(tmp_path)
    payload = json.loads(provider.calls[2]["content"])
    assert payload["challenge_contract"]["required_proposer_response_ids"] == ["C1"]
    assert payload["challenge_contract"]["latest_critic_message"] == "r1-critic"


def test_all_summary_reference_errors_return_in_one_repair():
    from deliberation.validation import validate_decision

    document = decision()
    document["agreed_included_scope"] = [dict(document["agreed_excluded_scope"][0])]
    for field in ["agreed_included_scope", "agreed_excluded_scope"]:
        document[field][0]["supporting_messages"] = ["r1-proposer"]
    with pytest.raises(ValueError) as caught:
        validate_decision(
            Decision.model_validate(document), [{"message_id": "r1-proposer", "role": "proposer"}]
        )
    assert "agreed_included_scope[0]" in str(caught.value)
    assert "agreed_excluded_scope[0]" in str(caught.value)
