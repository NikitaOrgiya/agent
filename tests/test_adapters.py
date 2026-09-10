"""Provider adapters against a mocked HTTP transport (no network, no real key)."""

import httpx
import pytest

from app.adapters.anthropic import AnthropicAdapter
from app.adapters.openai_compatible import OpenAICompatibleAdapter
from app.core.enums import ModelResponseKind, ModelStatus
from app.core.model import ModelRequest

pytestmark = pytest.mark.asyncio

_SECRET_KEY = "sk-do-not-leak-me-123456"


def _patch(monkeypatch, handler):
    real = httpx.AsyncClient

    def factory(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        kwargs.pop("timeout", None)
        return real(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", factory)


async def test_openai_adapter_parses_answer_and_usage(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == f"Bearer {_SECRET_KEY}"
        return httpx.Response(
            200,
            json={
                "model": "gpt-x",
                "choices": [{"message": {"content": "hello there"}}],
                "usage": {"prompt_tokens": 5, "completion_tokens": 7},
            },
        )

    _patch(monkeypatch, handler)
    adapter = OpenAICompatibleAdapter(
        api_key=_SECRET_KEY, model="gpt-x", base_url="https://api.example/v1"
    )
    resp = await adapter.generate(ModelRequest(prompt="hi", system="sys"))
    assert resp.status is ModelStatus.OK
    assert resp.text == "hello there"
    assert resp.input_tokens == 5 and resp.output_tokens == 7
    assert resp.cost_usd is None


async def test_openai_adapter_auth_error_does_not_leak_key(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "bad key"})

    _patch(monkeypatch, handler)
    adapter = OpenAICompatibleAdapter(
        api_key=_SECRET_KEY, model="gpt-x", base_url="https://api.example/v1"
    )
    resp = await adapter.generate(ModelRequest(prompt="hi"))
    assert resp.status is ModelStatus.MODEL_ERROR
    assert "authentication failed" in (resp.error or "")
    assert _SECRET_KEY not in (resp.error or "")


async def test_openai_adapter_detects_clarification(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "NEEDS_CLARIFICATION: which repo?"}}]},
        )

    _patch(monkeypatch, handler)
    adapter = OpenAICompatibleAdapter(
        api_key=_SECRET_KEY, model="gpt-x", base_url="https://api.example/v1"
    )
    resp = await adapter.generate(ModelRequest(prompt="deploy it"))
    assert resp.kind is ModelResponseKind.NEEDS_CLARIFICATION
    assert resp.clarification_question == "which repo?"
    assert resp.text is None


async def test_anthropic_adapter_parses_answer(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["x-api-key"] == _SECRET_KEY
        return httpx.Response(
            200,
            json={
                "model": "claude-x",
                "content": [{"type": "text", "text": "anthropic says hi"}],
                "usage": {"input_tokens": 3, "output_tokens": 9},
            },
        )

    _patch(monkeypatch, handler)
    adapter = AnthropicAdapter(api_key=_SECRET_KEY, model="claude-x")
    resp = await adapter.generate(ModelRequest(prompt="hi", system="sys"))
    assert resp.status is ModelStatus.OK
    assert resp.text == "anthropic says hi"
    assert resp.input_tokens == 3 and resp.output_tokens == 9
