"""Liveness and readiness endpoints (no authentication).

Neither endpoint returns credentials, a DSN, or a stack trace.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.db import get_session

logger = logging.getLogger("agentos.api.health")
router = APIRouter(tags=["system"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Process is alive. Does not touch any dependency."""
    return {"status": "ok", "service": "agent-os-kernel"}


@router.get("/readiness")
async def readiness(session: AsyncSession = Depends(get_session)):
    """V1 dependencies required to serve traffic are reachable (currently: DB)."""
    checks: dict[str, str] = {}
    ready = True

    try:
        await session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        logger.warning("readiness: database check failed", exc_info=True)
        checks["database"] = "error"
        ready = False

    body = {"status": "ready" if ready else "not_ready", "checks": checks}
    if not ready:
        return JSONResponse(status_code=503, content=body)
    return body
