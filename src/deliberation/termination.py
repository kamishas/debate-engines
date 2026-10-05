"""Critic-led stopping, with Python enforcing the accepted signal's conditions.

From round 2, valid completion or a justified stall ends deliberation. max_rounds
is a configurable safety ceiling (CLI: --max-rounds), not a target or evidence of
agreement. It only returns "capped" when neither valid signal is present.
Confidence and text similarity do not determine termination.
"""

from .schemas import Critique


def stopping_decision(critique: Critique, completed_rounds: int, max_rounds: int):
    if max_rounds < 2:
        raise ValueError("max_rounds must permit at least two complete rounds")
    blockers = any(item.blocks_agreement for item in critique.challenges)
    if completed_rounds >= 2:
        if critique.assessment == "complete" and not blockers:
            return "completed", critique.assessment_reason
        if critique.assessment == "stalled" and blockers:
            return "stalled", critique.assessment_reason
    # Explicit completion or a justified stall wins on the last allowed round.
    if completed_rounds >= max_rounds:
        return "capped", "Round cap reached without valid completion or a justified stall."
    return None
