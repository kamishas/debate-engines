"""Synchronous loop, in-memory dialogue, bounded calls, separate summarization."""

import json
import time
from dataclasses import asdict, dataclass
from importlib.resources import files
from pathlib import Path

from pydantic import ValidationError

from .logging import RunLog, now
from .provider import ProviderError
from .schemas import AgentConfidence, Critique, Decision, FinalDocument, Proposal
from .termination import stopping_decision
from .validation import challenge_contract, validate_decision, validate_turn


@dataclass(frozen=True)
class Settings:
    model: str = "claude-haiku-4-5-20251001"
    # Configurable safety ceiling; validated Critic signals can stop earlier.
    max_rounds: int = 8
    max_tokens: int = 8192
    max_calls: int = 24
    max_input_bytes: int = 500_000
    repair_attempts: int = 2
    provider_retries: int = 1

    def __post_init__(self):
        if not self.model.startswith("claude-") or "haiku" not in self.model.lower():
            raise ValueError(
                "Choose an explicit Claude Haiku model; no family substitution is allowed."
            )
        if not 2 <= self.max_rounds <= 20:
            raise ValueError("max_rounds must be between 2 and 20")
        if not 256 <= self.max_tokens <= 8192:
            raise ValueError("max_tokens must be between 256 and 8192")
        if not 1 <= self.max_calls <= 100:
            raise ValueError("max_calls must be between 1 and 100")
        if not 1024 <= self.max_input_bytes <= 500_000:
            raise ValueError("max_input_bytes must be between 1024 and 500000")
        if not 0 <= self.repair_attempts <= 2 or not 0 <= self.provider_retries <= 2:
            raise ValueError("Repair attempts and provider retries must be between 0 and 2")


class RunError(RuntimeError):
    pass


class Engine:
    def __init__(self, provider, settings: Settings, *, sleeper=time.sleep):
        self.provider = provider
        self.settings = settings
        self.sleeper = sleeper

    def _save_metadata(self):
        self.log.write("metadata.json", self.metadata)

    def _ask(self, role, round_number, schema):
        system = files("deliberation").joinpath("prompts", role + ".md").read_text(encoding="utf-8")
        payload = {
            "original_request": self.request,
            "system_context": self.context,
            "dialogue": self.dialogue,
            "termination": {
                "outcome": self.metadata["outcome"],
                "reason": self.metadata["termination_reason"],
                "completed_rounds": self.metadata["completed_rounds"],
            },
            "output_schema": schema.model_json_schema(),
        }
        if role == "summarizer":
            payload["message_index"] = [
                {key: exchange[key] for key in ("message_id", "role", "round")}
                for exchange in self.dialogue
            ]
        else:
            payload.update(
                round=round_number,
                protocol_feedback="Round 1 cannot terminate. Completion is documentation readiness.",
                challenge_contract=challenge_contract(self.dialogue),
            )
        for repair in range(self.settings.repair_attempts + 1):
            content = json.dumps(payload, ensure_ascii=False)
            if len((system + content).encode("utf-8")) > self.settings.max_input_bytes:
                raise RunError(
                    "Configured input/context budget exceeded; full dialogue was not truncated."
                )
            reply = None
            for retry in range(self.settings.provider_retries + 1):
                if self.metadata["provider_calls"] >= self.settings.max_calls:
                    raise RunError("Model-call budget exhausted (including retries and repairs).")
                self.metadata["provider_calls"] += 1
                call_id = self.metadata["provider_calls"]
                self.log.event(
                    "call_started",
                    call_id=call_id,
                    role=role,
                    round=round_number,
                    repair=repair,
                    retry=retry,
                    system_prompt=system,
                    payload=payload,
                )
                self._save_metadata()
                try:
                    reply = self.provider.generate(
                        system=system,
                        content=content,
                        schema=schema,
                        max_tokens=self.settings.max_tokens,
                    )
                    break
                except ProviderError as exc:
                    self.log.event(
                        "provider_error",
                        call_id=call_id,
                        role=role,
                        round=round_number,
                        error=str(exc),
                        transient=exc.transient,
                    )
                    if not exc.transient or retry == self.settings.provider_retries:
                        raise RunError(str(exc)) from exc
                    self.sleeper(2**retry)
            assert reply is not None
            self.metadata["input_tokens"] += reply.input_tokens
            self.metadata["output_tokens"] += reply.output_tokens
            self.log.event(
                "model_response",
                call_id=call_id,
                role=role,
                round=round_number,
                repair=repair,
                validation="pending",
                **asdict(reply),
            )
            self._save_metadata()
            try:
                if reply.stop_reason != "end_turn":
                    raise ValueError(f"Unusable model response: stop_reason={reply.stop_reason}")
                message = schema.model_validate_json(reply.text)
                if role == "summarizer":
                    validate_decision(message, self.dialogue)
                else:
                    validate_turn(role, message, self.dialogue)
            except (ValidationError, ValueError) as exc:
                # Pydantic's default exception text includes input values; keep error feedback narrow.
                detail = (
                    json.dumps(exc.errors(include_input=False, include_url=False))
                    if isinstance(exc, ValidationError)
                    else str(exc)
                )
                self.log.event(
                    "validation_failed",
                    call_id=call_id,
                    role=role,
                    round=round_number,
                    error=detail,
                    repair_available=repair < self.settings.repair_attempts,
                )
                if repair == self.settings.repair_attempts:
                    raise RunError("Output validation exhausted bounded repair: " + detail) from exc
                payload["repair"] = {
                    "invalid_response": reply.text,
                    "validation_errors": detail,
                    "instruction": "Correct the JSON and protocol error only; this is the same turn.",
                }
                continue
            self.log.event("validation_passed", call_id=call_id, role=role, round=round_number)
            return message
        raise AssertionError("unreachable")

    def run(self, request: str, context: str, output: Path):
        if not request.strip() or not context.strip():
            raise ValueError("Feature request and system context must be non-empty.")
        self.request, self.context = request.strip(), context.strip()
        self.dialogue = []
        self.log = RunLog(output)
        self.metadata = {
            "model": self.settings.model,
            "settings": asdict(self.settings),
            "started_at": now(),
            "updated_at": now(),
            "completed_rounds": 0,
            "outcome": None,
            "termination_reason": "Deliberation is running.",
            "report_status": "pending",
            "provider_calls": 0,
            "input_tokens": 0,
            "output_tokens": 0,
        }
        self.log.write("input.json", {"request": self.request, "system_context": self.context})
        self._save_metadata()
        try:
            for round_number in range(1, self.settings.max_rounds + 1):
                for role, schema in (("proposer", Proposal), ("critic", Critique)):
                    message = self._ask(role, round_number, schema)
                    exchange = {
                        "message_id": f"r{round_number}-{role}",
                        "role": role,
                        "round": round_number,
                        "content": message.model_dump(),
                    }
                    self.dialogue.append(exchange)
                    self.log.event("exchange", **exchange)
                    self.metadata["updated_at"] = now()
                    if role == "critic":
                        self.metadata["completed_rounds"] = round_number
                    self._save_metadata()
                outcome = stopping_decision(message, round_number, self.settings.max_rounds)
                if outcome:
                    self.metadata["outcome"], self.metadata["termination_reason"] = outcome
                    break
                if message.assessment != "continue":
                    self.log.event(
                        "termination_deferred", reason="At least two complete rounds required."
                    )
        except (RunError, OSError) as exc:
            self.metadata["outcome"] = "error"
            self.metadata["termination_reason"] = str(exc)
            if isinstance(exc, OSError):
                # Writes may no longer work. Fail loudly rather than call more models without logs.
                raise RunError(
                    f"Output-writing failed; inspect preserved files at {self.log.path}"
                ) from exc
            self.log.event("deliberation_error", error=str(exc))
        except KeyboardInterrupt:
            self.metadata["outcome"] = "error"
            self.metadata["termination_reason"] = "Interrupted by user; start a new run."
            self.metadata["report_status"] = "skipped"
            self._save_metadata()
            raise
        self._save_metadata()
        self.log.event(
            "deliberation_stopped",
            outcome=self.metadata["outcome"],
            reason=self.metadata["termination_reason"],
        )
        if self.dialogue:
            self.metadata["report_status"] = "running"
            self._save_metadata()
            try:
                decision = self._ask("summarizer", self.metadata["completed_rounds"], Decision)
                confidence = {}
                for exchange in self.dialogue:
                    confidence[exchange["role"]] = AgentConfidence(
                        **exchange["content"]["confidence"],
                        round=exchange["round"],
                        message_id=exchange["message_id"],
                    )
                final = FinalDocument(
                    original_request=self.request,
                    system_context=self.context,
                    outcome=self.metadata["outcome"],
                    termination_reason=self.metadata["termination_reason"],
                    completed_rounds=self.metadata["completed_rounds"],
                    partial=self.metadata["outcome"] != "completed",
                    latest_confidence=confidence,
                    confidence_note="Self-reported judgments, not calibrated probabilities. Proposer "
                    "assesses defensibility; Critic assesses review readiness. "
                    "Subtracting scores is not a validated disagreement measure.",
                    decision=decision,
                )
                self.log.write("final.json", final.model_dump())
                self.metadata["report_status"] = "succeeded"
            except (RunError, OSError) as exc:
                self.metadata["report_status"] = "failed"
                self.metadata["report_error"] = str(exc)
                self.log.event("report_error", error=str(exc))
        else:
            self.metadata["report_status"] = "skipped"
        self.metadata["finished_at"] = now()
        self._save_metadata()
        self.log.event(
            "run_finished",
            outcome=self.metadata["outcome"],
            report_status=self.metadata["report_status"],
        )
        return self.log.path, self.metadata
