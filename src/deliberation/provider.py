"""One SDK call per attempt; retry/repair policy lives in the orchestrator."""

from dataclasses import dataclass

from anthropic import Anthropic, APIConnectionError, APIStatusError, transform_schema
from pydantic import BaseModel


class ProviderError(RuntimeError):
    def __init__(self, message: str, *, transient: bool = False):
        super().__init__(message)
        self.transient = transient


@dataclass
class Reply:
    text: str
    stop_reason: str = "end_turn"
    input_tokens: int = 0
    output_tokens: int = 0
    request_id: str | None = None


class AnthropicProvider:
    def __init__(self, model: str, timeout: float = 90.0):
        self.model = model
        # Disable SDK retries so the logged attempt budget is the actual call budget.
        self.client = Anthropic(max_retries=0, timeout=timeout)

    def close(self):
        self.client.close()

    def generate(self, *, system: str, content: str, schema: type[BaseModel], max_tokens: int):
        try:
            result = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": content}],
                output_config={
                    "format": {"type": "json_schema", "schema": transform_schema(schema)}
                },
            )
        except APIConnectionError as exc:
            raise ProviderError("Anthropic connection/timeout failure", transient=True) from exc
        except APIStatusError as exc:
            status = exc.status_code
            # Do not persist provider bodies/headers: they may contain content or credentials.
            message = f"Anthropic HTTP {status}"
            if status in (400, 413):
                message += (
                    ": invalid request, unsupported schema/model, or context limit; no truncation"
                )
            if status in (401, 403):
                message += ": check local credentials and model access"
            raise ProviderError(
                message, transient=status in (408, 409, 429) or status >= 500
            ) from exc
        return Reply(
            text="\n".join(block.text for block in result.content if block.type == "text"),
            stop_reason=result.stop_reason or "unknown",
            input_tokens=result.usage.input_tokens,
            output_tokens=result.usage.output_tokens,
            request_id=result._request_id,
        )
