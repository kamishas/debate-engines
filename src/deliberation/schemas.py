"""JSON contracts. Structural validity does not prove reasoning quality."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

Text = Annotated[str, Field(min_length=1)]
Outcome = Literal["completed", "stalled", "capped", "error"]


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)


class Confidence(Record):
    score: Annotated[int, Field(ge=0, le=100)]
    justification: Text
    main_uncertainty: Text


class HumanQuestion(Record):
    question: Text
    impact: Text
    blocks_implementation: bool


class Assumption(Record):
    id: Text
    statement: Text
    rationale: Text


class Response(Record):
    challenge_id: Text
    action: Literal["defend", "revise", "concede"]
    rationale: Text


class Proposal(Record):
    interpretation: Text
    supplied_facts: list[Text]
    included_scope: Annotated[list[Text], Field(min_length=1)]
    excluded_scope: list[Text]
    conditional_scope: list[Text]
    assumptions: list[Assumption]
    success_criteria: Annotated[list[Text], Field(min_length=1)]
    responses: list[Response]
    open_questions: list[HumanQuestion]
    confidence: Confidence


class Challenge(Record):
    id: Text
    target: Text
    concern: Text
    resolution_needed: Text
    blocks_agreement: bool


class Assessment(Record):
    challenge_id: Text
    disposition: Literal["resolved", "unresolved"]
    reason: Text


class Critique(Record):
    response_assessments: list[Assessment]
    accepted_points: list[Text]
    challenges: list[Challenge]
    open_questions: list[HumanQuestion]
    assessment: Literal["continue", "complete", "stalled"]
    assessment_reason: Text
    next_exchange: str
    confidence: Confidence


class Evidence(Record):
    statement: Text
    reason: Text
    supporting_messages: Annotated[list[Text], Field(min_length=1)]


class ReportAssumption(Evidence):
    disposition: Literal[
        "accepted", "challenged_and_retained", "revised", "rejected", "unresolved", "unreviewed"
    ]


class Criterion(Evidence):
    disposition: Literal["agreed", "proposed"]


class ReportQuestion(HumanQuestion):
    supporting_messages: Annotated[list[Text], Field(min_length=1)]


class Decision(Record):
    """Summarizer authors content; Python supplies immutable run facts."""

    summary: Text
    agreed_included_scope: list[Evidence]
    agreed_excluded_scope: list[Evidence]
    conditional_scope: list[Evidence]
    disputed_scope: list[Evidence]
    unresolved_scope: list[Evidence]
    assumptions: list[ReportAssumption]
    success_criteria: list[Criterion]
    open_human_questions: list[ReportQuestion]
    rejected_options: list[Evidence]


class AgentConfidence(Confidence):
    round: Annotated[int, Field(ge=1)]
    message_id: Text


class FinalDocument(Record):
    original_request: Text
    system_context: Text
    outcome: Outcome
    termination_reason: Text
    completed_rounds: Annotated[int, Field(ge=0)]
    partial: bool
    latest_confidence: dict[str, AgentConfidence]
    confidence_note: Text
    decision: Decision
