"""Anthropic Messages API adapter (plain httpx, no anthropic SDK)."""

from __future__ import annotations

import logging
import time

import httpx

from app.adapters._http import ModelCallError, classify_http_error
from app.core.enums import BudgetTier, ModelResponseKind, ModelStatus
from app.core.model import (
    ModelAdapter,
    ModelProfile,
    ModelRequest,
    ModelResponse,
    classify_model_text,
)

logger = logging.getLogger("agentos.adapters.anthropic")

_API_URL = "https://api.anthropic.com/v1/messages"
_API_VERSION = "2023-06-01"


class AnthropicAdapter(ModelAdapter):
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        profile: BudgetTier = BudgetTier.STANDARD,
        timeout_seconds: float = 60.0,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._profile = profile
        self._timeout = timeout_seconds

    def profile(self) -> ModelProfile:
        return ModelProfile(
            provider="anthropic",
            model=self._model,
            profile=self._profile,
            context_window=0,
            available=True,
        )

    async def generate(self, request: ModelRequest) -> ModelResponse:
        messages = [
            {"role": m["role"], "content": m["content"]} for m in request.history
        ]
        messages.append({"role": "user", "content": request.prompt})

        payload: dict[str, object] = {
            "model": self._model,
            "max_tokens": request.max_output_tokens,
            "messages": messages,
        }
        if request.system:
            payload["system"] = request.system

        started = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    _API_URL,
                    headers={
                        "x-api-key": self._api_key,
                        "anthropic-version": _API_VERSION,
                        "content-type": "application/json",
                    },
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:  # noqa: BLE001 - normalised; key never logged
            err: ModelCallError = classify_http_error(exc)
            logger.warning("anthropic call failed: %s", err)
            return ModelResponse(
                status=ModelStatus.MODEL_ERROR,
                provider="anthropic",
                model=self._model,
                profile=request.profile,
                prompt_version=request.prompt_version,
                latency_ms=int((time.monotonic() - started) * 1000),
                error=str(err),
            )

        latency_ms = int((time.monotonic() - started) * 1000)
        blocks = data.get("content") or []
        text = next(
            (b.get("text") for b in blocks if isinstance(b, dict) and b.get("type") == "text"),
            None,
        )
        usage = data.get("usage") or {}
        kind, answer, question = classify_model_text(text)
        return ModelResponse(
            status=ModelStatus.OK,
            kind=kind,
            text=answer if kind is ModelResponseKind.ANSWER else None,
            clarification_question=question,
            provider="anthropic",
            model=data.get("model") or self._model,
            profile=request.profile,
            prompt_version=request.prompt_version,
            latency_ms=latency_ms,
            input_tokens=usage.get("input_tokens"),
            output_tokens=usage.get("output_tokens"),
            cost_usd=None,
        )
