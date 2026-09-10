"""Provider-neutral model adapter interface.

No provider is wired here. The point of Sprint 1 is only the seam: a future
Model Router can register OpenAI / Anthropic / open-weight adapters behind this
interface without the Courier core changing.

The only concrete implementation for now is ``NullModelAdapter``, which is
honest about the absence of a model (``MODEL_UNAVAILABLE``) instead of
fabricating an answer. This is the "No fabrication by design" principle applied
to the execution layer.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from app.core.enums import ModelStatus


@dataclass(frozen=True)
class ModelRequest:
    prompt: str
    purpose: str = "general"
    max_output_tokens: int = 1024
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ModelResponse:
    status: ModelStatus
    text: str | None = None
    provider: str | None = None
    model: str | None = None
    usage: dict[str, int] = field(default_factory=dict)
    error: str | None = None


@dataclass(frozen=True)
class ModelProfile:
    provider: str
    model: str
    context_window: int
    strengths: tuple[str, ...] = ()
    available: bool = False


class ModelAdapter(ABC):
    """A single model provider behind a stable interface."""

    @abstractmethod
    def profile(self) -> ModelProfile:
        """Static capability / availability description used by the future Router."""

    @abstractmethod
    async def generate(self, request: ModelRequest) -> ModelResponse:
        """Run one request. Must never fabricate output on failure."""


class NullModelAdapter(ModelAdapter):
    """Default adapter: no provider connected."""

    _REASON = (
        "No model provider is configured. Execution intelligence is not "
        "connected yet (planned for a later sprint)."
    )

    def profile(self) -> ModelProfile:
        return ModelProfile(
            provider="none",
            model="none",
            context_window=0,
            strengths=(),
            available=False,
        )

    async def generate(self, request: ModelRequest) -> ModelResponse:
        return ModelResponse(
            status=ModelStatus.MODEL_UNAVAILABLE,
            text=None,
            provider="none",
            model="none",
            error=self._REASON,
        )
