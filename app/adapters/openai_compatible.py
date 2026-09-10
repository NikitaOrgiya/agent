"""OpenAI / OpenAI-compatible Chat Completions adapter.

Works against api.openai.com and any endpoint that speaks the same
``POST /chat/completions`` shape (many self-hosted and third-party gateways do).
"""

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

logger = logging.getLogger("agentos.adapters.openai")


class OpenAICompatibleAdapter(ModelAdapter):
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str,
        provider_label: str = "openai",
        profile: BudgetTier = BudgetTier.STANDARD,
        timeout_seconds: float = 60.0,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._provider = provider_label
        self._profile = profile
        self._timeout = timeout_seconds

    def profile(self) -> ModelProfile:
        return ModelProfile(
            provider=self._provider,
            model=self._model,
            profile=self._profile,
            context_window=0,
            available=True,
        )

    async def generate(self, request: ModelRequest) -> ModelResponse:
        messages: list[dict[str, str]] = []
        if request.system:
            messages.append({"role": "system", "content": request.system})
        messages.extend({"role": m["role"], "content": m["content"]} for m in request.history)
        messages.append({"role": "user", "content": request.prompt})

        payload = {
            "model": self._model,
            "messages": messages,
            "max_tokens": request.max_output_tokens,
        }
        started = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    f"{self._base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:  # noqa: BLE001 - normalised below; key never logged
            err: ModelCallError = classify_http_error(exc)
            logger.warning("openai-compatible call failed: %s", err)
            return ModelResponse(
                status=ModelStatus.MODEL_ERROR,
                provider=self._provider,
                model=self._model,
                profile=request.profile,
                prompt_version=request.prompt_version,
                latency_ms=int((time.monotonic() - started) * 1000),
                error=str(err),
            )

        latency_ms = int((time.monotonic() - started) * 1000)
        text = (
            data.get("choices", [{}])[0].get("message", {}).get("content")
            if data.get("choices")
            else None
        )
        usage = data.get("usage") or {}
        kind, answer, question = classify_model_text(text)
        return ModelResponse(
            status=ModelStatus.OK,
            kind=kind,
            text=answer if kind is ModelResponseKind.ANSWER else None,
            clarification_question=question,
            provider=self._provider,
            model=data.get("model") or self._model,
            profile=request.profile,
            prompt_version=request.prompt_version,
            latency_ms=latency_ms,
            input_tokens=usage.get("prompt_tokens"),
            output_tokens=usage.get("completion_tokens"),
            cost_usd=None,  # provider does not return cost; never guess
        )
