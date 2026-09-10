"""Concrete model provider adapters and the router factory.

Adapters use plain ``httpx`` (already a dependency) -- no provider SDK. A
provider is turned on only by configuration; with ``MODEL_PROVIDER=none`` the
router has nothing available and the system stays honest (MODEL_UNAVAILABLE).

API keys come from env only and never appear in logs, errors, audit, or the
``/models`` listing.
"""

from __future__ import annotations

import logging

from app.adapters.anthropic import AnthropicAdapter
from app.adapters.openai_compatible import OpenAICompatibleAdapter
from app.config import Settings
from app.core.enums import BudgetTier
from app.core.model import NullModelAdapter
from app.core.router import ModelRouter

logger = logging.getLogger("agentos.adapters")

_OPENAI_DEFAULT_BASE = "https://api.openai.com/v1"


def build_router(settings: Settings) -> ModelRouter:
    """Construct the ModelRouter from settings. Always safe to call."""
    router = ModelRouter()
    default_tier = BudgetTier(settings.default_model_profile.strip().lower())
    router.set_default(NullModelAdapter(profile_tier=default_tier))

    provider = settings.model_provider.strip().lower()
    adapter = None
    try:
        if provider in {"openai", "openai_compatible"}:
            base_url = (
                settings.model_base_url.strip()
                if provider == "openai_compatible" and settings.model_base_url.strip()
                else _OPENAI_DEFAULT_BASE
            )
            if settings.openai_api_key.strip() and settings.model_name.strip():
                adapter = OpenAICompatibleAdapter(
                    api_key=settings.openai_api_key.strip(),
                    model=settings.model_name.strip(),
                    base_url=base_url,
                    provider_label="openai" if provider == "openai" else "openai_compatible",
                    profile=default_tier,
                    timeout_seconds=settings.model_timeout_seconds,
                )
        elif provider == "anthropic":
            if settings.anthropic_api_key.strip() and settings.model_name.strip():
                adapter = AnthropicAdapter(
                    api_key=settings.anthropic_api_key.strip(),
                    model=settings.model_name.strip(),
                    profile=default_tier,
                    timeout_seconds=settings.model_timeout_seconds,
                )
    except Exception:
        logger.exception("failed to build model adapter for provider %r", provider)
        adapter = None

    if adapter is not None:
        # One real adapter serves every profile in Sprint 2.
        for tier in BudgetTier:
            router.register(tier, adapter)
        logger.info("model router: provider %r registered for all profiles", provider)
    else:
        if provider != "none":
            logger.warning(
                "MODEL_PROVIDER=%r but adapter not built (missing key or model name); "
                "staying MODEL_UNAVAILABLE",
                provider,
            )

    return router


__all__ = ["AnthropicAdapter", "OpenAICompatibleAdapter", "build_router"]
