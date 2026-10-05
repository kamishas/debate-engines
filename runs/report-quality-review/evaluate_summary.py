"""One-off, bounded Summarizer evaluation of a frozen accepted dialogue.

This is an evaluation artifact, not a resume command or production feature.
Original run files are read only. Each invocation permits at most three calls.
The final evaluation pass uses --attempts 1 to stay within the total budget.
"""

import argparse
import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from dotenv import load_dotenv

from deliberation.engine import Engine, RunError, Settings
from deliberation.logging import RunLog, now
from deliberation.provider import AnthropicProvider
from deliberation.schemas import AgentConfidence, Decision, FinalDocument


def fingerprints(path):
    return {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(path.iterdir()) if p.is_file()
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--label", required=True, choices=("placeholder", "capped", "error"))
    parser.add_argument("--attempts", type=int, choices=(1, 3), default=3)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    source = args.source.resolve()
    before = fingerprints(source)
    previous = json.loads((source / "metadata.json").read_text(encoding="utf-8"))
    inputs = json.loads((source / "input.json").read_text(encoding="utf-8"))
    events = [
        json.loads(line)
        for line in (source / "exchanges.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    dialogue = [
        {key: event[key] for key in ("message_id", "role", "round", "content")}
        for event in events if event["event"] == "exchange"
    ]
    settings = Settings(
        model=previous["model"],
        max_rounds=previous["settings"]["max_rounds"],
        max_tokens=8192,
        max_calls=args.attempts,
        max_input_bytes=500000,
        repair_attempts=args.attempts - 1,
        provider_retries=0,
    )
    load_dotenv(root / ".env", override=False)
    provider = AnthropicProvider(settings.model)
    engine = Engine(provider, settings)
    engine.request = inputs["request"]
    engine.context = inputs["system_context"]
    engine.dialogue = dialogue
    engine.log = RunLog(root / "runs" / "report-quality-review" / args.label)
    engine.metadata = {
        "evaluation_type": "summarizer_only_on_frozen_dialogue",
        "case": args.label,
        "source_run": str(source),
        "source_report_status": previous["report_status"],
        "source_file_hashes": before,
        "model": settings.model,
        "settings": asdict(settings),
        "started_at": now(),
        "outcome": previous["outcome"],
        "termination_reason": previous["termination_reason"],
        "completed_rounds": previous["completed_rounds"],
        "report_status": "running",
        "provider_calls": 0,
        "input_tokens": 0,
        "output_tokens": 0,
    }
    engine.log.write("input.json", {
        **inputs,
        "source_run": str(source),
        "dialogue": dialogue,
        "note": "Frozen accepted messages only; no Proposer or Critic calls are made.",
    })
    engine._save_metadata()
    try:
        decision = engine._ask("summarizer", previous["completed_rounds"], Decision)
        confidence = {}
        for exchange in dialogue:
            confidence[exchange["role"]] = AgentConfidence(
                **exchange["content"]["confidence"],
                round=exchange["round"],
                message_id=exchange["message_id"],
            )
        final = FinalDocument(
            original_request=engine.request,
            system_context=engine.context,
            outcome=previous["outcome"],
            termination_reason=previous["termination_reason"],
            completed_rounds=previous["completed_rounds"],
            partial=previous["outcome"] != "completed",
            latest_confidence=confidence,
            confidence_note="Self-reported judgments, not calibrated probabilities. Proposer "
            "assesses defensibility; Critic assesses review readiness. "
            "Subtracting scores is not a validated disagreement measure.",
            decision=decision,
        )
        engine.log.write("final.json", final.model_dump())
        engine.metadata["report_status"] = "succeeded"
    except (RunError, OSError) as exc:
        engine.metadata["report_status"] = "failed"
        engine.metadata["report_error"] = str(exc)
        engine.log.event("report_error", error=str(exc))
    finally:
        provider.close()
        engine.metadata["source_files_unchanged"] = before == fingerprints(source)
        engine.metadata["finished_at"] = now()
        engine._save_metadata()
        engine.log.event("evaluation_finished", report_status=engine.metadata["report_status"])
    print(json.dumps({
        "case": args.label,
        "path": str(engine.log.path),
        **{key: engine.metadata[key] for key in (
            "report_status", "provider_calls", "input_tokens", "output_tokens",
            "source_files_unchanged",
        )},
    }), flush=True)
    return 0 if engine.metadata["report_status"] == "succeeded" else 1


if __name__ == "__main__":
    raise SystemExit(main())
