"""Test doubles for model adapters (no network, no provider)."""

from __future__ import annotations

from app.core.enums import BudgetTier, ModelResponseKind, ModelStatus
from app.core.model import ModelAdapter, ModelProfile, ModelRequest, ModelResponse


class FakeAdapter(ModelAdapter):
    """Scripted adapter. ``script`` is a list of ModelResponse to return in order;
    the last one repeats."""

    def __init__(self, script: list[ModelResponse], *, available: bool = True) -> None:
        self._script = script
        self._available = available
        self.calls: list[ModelRequest] = []

    def profile(self) -> ModelProfile:
        return ModelProfile(
            provider="fake",
            model="fake-1",
            profile=BudgetTier.STANDARD,
            context_window=8000,
            available=self._available,
        )

    async def generate(self, request: ModelRequest) -> ModelResponse:
        self.calls.append(request)
        idx = min(len(self.calls) - 1, len(self._script) - 1)
        return self._script[idx]


def answer(text: str) -> ModelResponse:
    return ModelResponse(
        status=ModelStatus.OK,
        kind=ModelResponseKind.ANSWER,
        text=text,
        provider="fake",
        model="fake-1",
        profile=BudgetTier.STANDARD,
        prompt_version="courier-v1",
        latency_ms=5,
        input_tokens=10,
        output_tokens=20,
    )


def clarify(question: str) -> ModelResponse:
    return ModelResponse(
        status=ModelStatus.OK,
        kind=ModelResponseKind.NEEDS_CLARIFICATION,
        clarification_question=question,
        provider="fake",
        model="fake-1",
        profile=BudgetTier.STANDARD,
        prompt_version="courier-v1",
        latency_ms=5,
    )


def error(message: str) -> ModelResponse:
    return ModelResponse(
        status=ModelStatus.MODEL_ERROR,
        provider="fake",
        model="fake-1",
        profile=BudgetTier.STANDARD,
        error=message,
    )


def router_with(adapter: ModelAdapter):
    from app.core.router import ModelRouter

    r = ModelRouter(retry_transient=False)
    for tier in BudgetTier:
        r.register(tier, adapter)
    r.set_default(adapter)
    return r
