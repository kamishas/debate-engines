"""CLI loads inputs, selects bounded settings, and reports actionable failures."""

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from .engine import Engine, RunError, Settings
from .logging import redact
from .provider import AnthropicProvider


def main(argv=None):
    load_dotenv(Path.cwd() / ".env", override=False)
    defaults = Settings()
    parser = argparse.ArgumentParser(description="Deliberate on an ambiguous feature request.")
    request = parser.add_mutually_exclusive_group(required=True)
    request.add_argument("--request", help="Feature request text")
    request.add_argument("--request-file", type=Path, help="UTF-8 text file")
    parser.add_argument("--context", type=Path, required=True, help="UTF-8 system context file")
    parser.add_argument("--output", type=Path, default=Path("runs"))
    parser.add_argument("--model", default=os.environ.get("ANTHROPIC_MODEL", defaults.model))
    parser.add_argument(
        "--max-rounds",
        type=int,
        default=defaults.max_rounds,
        help="Safety ceiling, not a target; valid Critic signals can stop earlier (default: %(default)s)",
    )
    parser.add_argument("--max-tokens", type=int, default=defaults.max_tokens)
    parser.add_argument("--max-calls", type=int, default=defaults.max_calls)
    parser.add_argument("--max-input-bytes", type=int, default=defaults.max_input_bytes)
    parser.add_argument("--repair-attempts", type=int, default=defaults.repair_attempts)
    parser.add_argument("--provider-retries", type=int, default=defaults.provider_retries)
    args = parser.parse_args(argv)
    provider = None
    try:
        feature = (
            args.request_file.read_text(encoding="utf-8-sig") if args.request_file else args.request
        )
        context = args.context.read_text(encoding="utf-8-sig")
        if not feature.strip() or not context.strip():
            raise ValueError("Feature request and context must not be empty.")
        settings = Settings(**{name: getattr(args, name) for name in Settings.__dataclass_fields__})
        key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
        if not key or key == "replace_locally_never_commit":
            raise ValueError(
                "ANTHROPIC_API_KEY is missing. Configure it locally; never paste it in chat."
            )
        provider = AnthropicProvider(settings.model)
        path, metadata = Engine(provider, settings).run(feature, context, args.output)
        print(f"Run: {path.resolve()}")
        print(f"Deliberation: {metadata['outcome']} ({metadata['completed_rounds']} rounds)")
        print(f"Report: {metadata['report_status']}; model calls: {metadata['provider_calls']}")
        print(redact(metadata["termination_reason"]))
        if metadata.get("report_error"):
            print(redact(metadata["report_error"]), file=sys.stderr)
        return (
            1 if metadata["outcome"] == "error" or metadata["report_status"] != "succeeded" else 0
        )
    except (OSError, UnicodeError, ValueError, RunError) as exc:
        print("Error: " + redact(str(exc)), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Interrupted. Existing logs are preserved; start a new run.", file=sys.stderr)
        return 130
    finally:
        if provider is not None:
            provider.close()
