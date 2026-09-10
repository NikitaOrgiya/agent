"""Shared HTTP helpers for model adapters. No provider SDK, just httpx."""

from __future__ import annotations

import httpx

# Status codes that are worth exactly one retry (see ModelRouter). Auth (401/403),
# bad request (400) and not-found (404) are never retried.
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class ModelCallError(Exception):
    def __init__(self, message: str, *, retryable: bool) -> None:
        super().__init__(message)
        self.retryable = retryable


def classify_http_error(exc: Exception) -> ModelCallError:
    if isinstance(exc, httpx.TimeoutException):
        return ModelCallError("model request timed out", retryable=True)
    if isinstance(exc, httpx.TransportError):
        return ModelCallError("connection error contacting model provider", retryable=True)
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        if code in (401, 403):
            return ModelCallError("model provider authentication failed", retryable=False)
        if code == 404:
            return ModelCallError("model not found at provider", retryable=False)
        if code == 400:
            return ModelCallError("model provider rejected the request (400)", retryable=False)
        if code in _RETRYABLE_STATUS:
            return ModelCallError(
                f"model provider temporarily unavailable ({code})", retryable=True
            )
        return ModelCallError(f"model provider error ({code})", retryable=False)
    return ModelCallError(f"unexpected model client error: {type(exc).__name__}", retryable=False)
