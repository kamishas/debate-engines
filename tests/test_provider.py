"""Exercise the real SDK with an in-process HTTP transport, never the network."""

import json

import httpx2 as httpx
import pytest
from anthropic import Anthropic

from deliberation.provider import AnthropicProvider, ProviderError
from deliberation.schemas import Confidence


def client_for(handler):
    provider = AnthropicProvider.__new__(AnthropicProvider)
    provider.model = "claude-haiku-4-5-20251001"
    provider.client = Anthropic(
        api_key="synthetic-offline-key",
        max_retries=0,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    return provider


def test_sdk_wire_shape_and_usage():
    seen = []

    def handler(request):
        body = json.loads(request.content)
        seen.append(body)
        assert body["model"] == "claude-haiku-4-5-20251001"
        assert body["output_config"]["format"]["type"] == "json_schema"
        assert body["messages"] == [{"role": "user", "content": "input"}]
        schema = body["output_config"]["format"]["schema"]
        assert schema["additionalProperties"] is False
        assert "minimum" not in schema["properties"]["score"]
        return httpx.Response(
            200,
            headers={"request-id": "synthetic-request"},
            json={
                "id": "msg_test",
                "type": "message",
                "role": "assistant",
                "model": body["model"],
                "content": [{"type": "text", "text": "{}"}],
                "stop_reason": "end_turn",
                "stop_sequence": None,
                "usage": {"input_tokens": 12, "output_tokens": 2},
            },
        )

    provider = client_for(handler)
    try:
        reply = provider.generate(
            system="system", content="input", schema=Confidence, max_tokens=1000
        )
    finally:
        provider.close()
    assert len(seen) == 1
    assert reply.input_tokens == 12
    assert reply.output_tokens == 2
    assert reply.request_id == "synthetic-request"


@pytest.mark.parametrize("status,transient", [(429, True), (500, True), (401, False), (400, False)])
def test_provider_error_classification_never_logs_body(status, transient):
    def handler(request):
        return httpx.Response(
            status,
            json={
                "type": "error",
                "error": {"type": "api_error", "message": "SENSITIVE_BODY_DO_NOT_LOG"},
            },
        )

    provider = client_for(handler)
    try:
        with pytest.raises(ProviderError) as caught:
            provider.generate(system="x", content="y", schema=Confidence, max_tokens=1000)
    finally:
        provider.close()
    assert caught.value.transient is transient
    assert "SENSITIVE_BODY" not in str(caught.value)
