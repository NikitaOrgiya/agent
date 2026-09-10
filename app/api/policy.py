import logging

from fastapi import APIRouter

from app.core.enums import PolicyDecision
from app.core.policy import PolicyEngine
from app.core.schemas import CapabilityRequest, PolicyResult

logger = logging.getLogger("agentos.policy.api")
router = APIRouter(prefix="/v1/policy", tags=["policy"])
engine = PolicyEngine()


@router.post("/check", response_model=PolicyResult)
async def check_policy(payload: CapabilityRequest) -> PolicyResult:
    try:
        return engine.check(payload)
    except Exception:  # noqa: BLE001 - fail closed: never surface ALLOW on error
        logger.exception("policy endpoint error; denying request")
        return PolicyResult(
            decision=PolicyDecision.DENY,
            reason="Policy evaluation failed; denying by default.",
            matched_rule="EVALUATION_ERROR",
        )
