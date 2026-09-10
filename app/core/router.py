"""Model Router.

Selects a ``ModelAdapter`` by logical profile (economy / standard / strong /
critical). The Courier and Intelligence Zone ask the router for a profile; they
never see a provider SDK or an endpoint.

Sprint 2 does not run four paid models. Typically one provider adapter is
registered (for one or more profiles) plus the always-present unavailable
fallback.
"""

from __future__ import annotations

import asyncio
import logging

from app.core.enums import BudgetTier, ModelStatus
from app.core.model import ModelAdapter, ModelProfile, ModelRequest, ModelResponse, NullModelAdapter

logger = logging.getLogger("agentos.router")

# Errors where a single careful retry is reasonable. Auth / billing / not-found
# are never retried (they will not fix themselves and can waste money).
_TRANSIENT_MARKERS = ("timeout", "timed out", "connection", "temporarily", "503", "502", "504", "overloaded")


class ModelRouter:
    def __init__(self, *, retry_transient: bool = True) -> None:
        self._by_profile: dict[BudgetTier, ModelAdapter] = {}
        self._default: ModelAdapter = NullModelAdapter()
        self._retry_transient = retry_transient

    def register(self, profile: BudgetTier, adapter: ModelAdapter) -> None:
        self._by_profile[profile] = adapter

    def set_default(self, adapter: ModelAdapter) -> None:
        self._default = adapter

    def resolve(self, profile: BudgetTier | None) -> ModelAdapter:
        if profile is not None and profile in self._by_profile:
            return self._by_profile[profile]
        return self._default

    def profiles(self) -> list[ModelProfile]:
        """Credential-free metadata for every distinct registered adapter."""
        seen: dict[int, ModelProfile] = {}
        for adapter in (*self._by_profile.values(), self._default):
            p = adapter.profile()
            seen[id(adapter)] = p
        return list(seen.values())

    def has_available_model(self) -> bool:
        return any(p.available for p in self.profiles())

    async def generate(self, request: ModelRequest) -> ModelResponse:
        adapter = self.resolve(request.profile)
        response = await self._call(adapter, request)
        if (
            self._retry_transient
            and response.status is ModelStatus.MODEL_ERROR
            and _is_transient(response.error)
        ):
            logger.warning("transient model error; one retry: %s", response.error)
            await asyncio.sleep(0.5)
            response = await self._call(adapter, request)
        return response

    async def _call(self, adapter: ModelAdapter, request: ModelRequest) -> ModelResponse:
        try:
            return await adapter.generate(request)
        except Exception as exc:
            logger.exception("model adapter raised")
            return ModelResponse(
                status=ModelStatus.MODEL_ERROR,
                profile=request.profile,
                prompt_version=request.prompt_version,
                error=f"{type(exc).__name__}: {exc}",
            )


def _is_transient(error: str | None) -> bool:
    if not error:
        return False
    low = error.lower()
    return any(marker in low for marker in _TRANSIENT_MARKERS)
