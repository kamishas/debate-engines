"""Append-and-flush audit files, plus atomically replaced metadata."""

import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4


def now():
    return datetime.now(UTC).isoformat()


def redact(text: str) -> str:
    secret = os.environ.get("ANTHROPIC_API_KEY")
    if secret:
        text = text.replace(secret, "[REDACTED]")
    return re.sub(r"sk-ant-[A-Za-z0-9_-]+", "[REDACTED]", text)


class RunLog:
    def __init__(self, output: Path):
        self.path = output / (datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ-") + uuid4().hex[:8])
        self.path.mkdir(parents=True, exist_ok=False)
        self.event("run_created", note="Audit log only. Interrupted runs cannot resume.")

    def _append(self, filename, content):
        with (self.path / filename).open("a", encoding="utf-8") as stream:
            stream.write(redact(content))
            stream.flush()
            os.fsync(stream.fileno())

    def event(self, kind: str, **data):
        event = {"timestamp": now(), "event": kind, **data}
        self._append("exchanges.jsonl", json.dumps(event, ensure_ascii=False) + "\n")
        self._append(
            "transcript.md",
            f"\n## {kind}\n\n```json\n{json.dumps(event, indent=2, ensure_ascii=False)}\n```\n",
        )

    def write(self, name: str, data):
        temporary = self.path / (name + ".tmp")
        with temporary.open("w", encoding="utf-8") as stream:
            stream.write(redact(json.dumps(data, indent=2, ensure_ascii=False)) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(self.path / name)
