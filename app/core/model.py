"""Provider-neutral model adapter interface.

The Courier and the Intelligence Zone talk to models only through this
interface, never through a provider SDK. ``ModelRouter`` (app/core/router.py)
sits on top and selects an adapter by logical profile.

``NullModelAdapter`` is the honest default: it returns ``MODEL_UNAVAILABLE``
instead of fabricating an answer ("No fabrication by design").
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from app.core.enums import BudgetTier, ModelResponseKind, ModelStatus

# Clarification convention: the system contract instructs the model to begin its
# reply with this exact token when it genuinely cannot proceed without more
# input. Kept out of the adapters' provider logic; classification is a pure
# function so Courier and tests share it.
CLARIFICATION_SENTINEL = "NEEDS_CLARIFICATION:"


@dataclass(frozen=True)
class ModelRequest:
    prompt: str
    system: str | None = None
    # Prior conversation, oldest first: [{"role": "user"|"assistant", "content": str}]
    history: tuple[dict[str, str], ...] = ()
    purpose: str = "general"
    profile: BudgetTier = BudgetTier.STANDARD
    max_output_tokens: int = 1024
    prompt_version: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ModelResponse:
    status: ModelStatus
    kind: ModelResponseKind = ModelResponseKind.ANSWER
    text: str | None = None
    # When kind == NEEDS_CLARIFICATION, the question to put to the owner.
    clarification_question: str | None = None
    provider: str | None = None
    model: str | None = None
    profile: BudgetTier | None = None
    prompt_version: str | None = None
    latency_ms: int | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    # Only set when the provider reports it reliably. None means "unknown" and
    # must never be guessed.
    cost_usd: float | None = None
    error: str | None = None


@dataclass(frozen=True)
class ModelProfile:
    provider: str
    model: str
    profile: BudgetTier
    context_window: int
    available: bool = False
    strengths: tuple[str, ...] = ()

    def public_dict(self) -> dict[str, object]:
        """Safe to show to the owner: no api key, no endpoint."""
        return {
            "provider": self.provider,
            "model": self.model,
            "profile": str(self.profile),
            "available": self.available,
            "context_window": self.context_window,
        }


class ModelAdapter(ABC):
    """A single model provider behind a stable interface."""

    @abstractmethod
    def profile(self) -> ModelProfile:
        """Static capability / availability description used by the Router."""

    @abstractmethod
    async def generate(self, request: ModelRequest) -> ModelResponse:
        """Run one request. Must never fabricate output on failure."""


class NullModelAdapter(ModelAdapter):
    """Default adapter: no provider connected."""

    _REASON = (
        "No model provider is configured. Set MODEL_PROVIDER and the matching "
        "API key to connect execution intelligence."
    )

    def __init__(self, profile_tier: BudgetTier = BudgetTier.STANDARD) -> None:
        self._tier = profile_tier

    def profile(self) -> ModelProfile:
        return ModelProfile(
            provider="none",
            model="none",
            profile=self._tier,
            context_window=0,
            available=False,
        )

    async def generate(self, request: ModelRequest) -> ModelResponse:
        return ModelResponse(
            status=ModelStatus.MODEL_UNAVAILABLE,
            provider="none",
            model="none",
            profile=request.profile,
            prompt_version=request.prompt_version,
            error=self._REASON,
        )


def classify_model_text(text: str | None) -> tuple[ModelResponseKind, str | None, str | None]:
    """Split a raw model reply into (kind, answer_text, clarification_question)."""
    if text is None:
        return ModelResponseKind.ANSWER, None, None
    stripped = text.lstrip()
    if stripped.startswith(CLARIFICATION_SENTINEL):
        question = stripped[len(CLARIFICATION_SENTINEL):].strip()
        return ModelResponseKind.NEEDS_CLARIFICATION, None, (question or "Could you clarify your request?")
    return ModelResponseKind.ANSWER, text, None
