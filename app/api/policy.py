from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import Principal, authorize_actor, require_principal
from app.core.enums import PolicyDecision
from app.core.policy import PolicyContext, PolicyEngine
from app.core.schemas import CapabilityRequest, PolicyResult
from app.infra.db import get_session
from app.services.audit import AuditService, outcome_for_decision

logger = logging.getLogger("agentos.policy.api")
router = APIRouter(prefix="/v1/policy", tags=["policy"])
engine = PolicyEngine()


@router.post("/check", response_model=PolicyResult)
async def check_policy(
    payload: CapabilityRequest,
    principal: Principal = Depends(require_principal),
    session: AsyncSession = Depends(get_session),
) -> PolicyResult:
    authorize_actor(principal, payload.actor)

    # The public API has no way to *verify* owner approval (that arrives with
    # Custodian). A client-sent `owner_approved: true` is therefore ignored:
    # the context always carries verified_owner_approval=False here.
    context = PolicyContext(verified_owner_approval=False)

    try:
        result = engine.check(payload, context)
    except Exception:
        logger.exception("policy endpoint error; denying request")
        result = PolicyResult(
            decision=PolicyDecision.DENY,
            reason="Policy evaluation failed; denying by default.",
            matched_rule="EVALUATION_ERROR",
        )

    try:
        await AuditService(session).record(
            actor=str(payload.actor),
            action=payload.action,
            resource=payload.resource or None,
            task_id=payload.task_id,
            decision=str(result.decision),
            outcome=outcome_for_decision(result.decision),
            reason=result.reason,
            extra={"matched_rule": result.matched_rule, "caller": principal.id},
        )
        await session.commit()
    except Exception:  # noqa: BLE001
        await session.rollback()
        logger.critical("audit persistence failed for policy check; failing closed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="audit trail unavailable; request was not recorded or evaluated",
        )

    return result
