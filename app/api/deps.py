"""API identity foundation for /v1/*.

Sprint 1 scope only: one Control Plane token authenticates a single caller
("control-plane"). This is deliberately minimal -- it is not Custodian, not a
master-secret architecture, and not a real identity system.

Key distinction that must exist even now:

    authenticated caller  != requested actor role

The token proves *a* caller is allowed to talk to the Control Plane. The
``actor`` / ``requested_actor`` field in the request body is only a *request* to
act as that role. A caller cannot become OWNER or CUSTODIAN just by putting it
in JSON: those roles are not requestable through this Sprint 1 token at all.
"""

from __future__ import annotations

import hmac
import logging
from dataclasses import dataclass

from fastapi import Header, HTTPException, status

from app.config import get_settings
from app.core.enums import AgentRole

logger = logging.getLogger("agentos.api.auth")

# Roles a plain Control Plane token caller may request. OWNER and CUSTODIAN are
# intentionally excluded until a real identity / capability system exists.
CONTROL_REQUESTABLE_ROLES: frozenset[AgentRole] = frozenset(
    {
        AgentRole.COURIER,
        AgentRole.LAB,
        AgentRole.RESEARCHER,
        AgentRole.ENGINEER,
        AgentRole.BROWSER,
        AgentRole.VERIFIER,
        AgentRole.GUARDIAN,
    }
)


@dataclass(frozen=True)
class Principal:
    id: str
    requestable_roles: frozenset[AgentRole]

    def may_request(self, role: AgentRole) -> bool:
        return role in self.requestable_roles


def _extract_bearer(authorization: str | None) -> str:
    if not authorization:
        return ""
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return ""
    return parts[1].strip()


async def require_principal(authorization: str | None = Header(default=None)) -> Principal:
    settings = get_settings()
    configured = settings.agentos_control_token.strip()
    if not configured:
        # Fail closed: no token configured => no authenticated access at all.
        logger.error("AGENTOS_CONTROL_TOKEN is not configured; refusing /v1 access")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="control plane authentication is not configured",
        )
    presented = _extract_bearer(authorization)
    if not presented or not hmac.compare_digest(presented, configured):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid or missing control token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Principal(id="control-plane", requestable_roles=CONTROL_REQUESTABLE_ROLES)


def authorize_actor(principal: Principal, requested: AgentRole) -> None:
    """Reject a request to act as a role the caller may not assume."""
    if not principal.may_request(requested):
        logger.warning(
            "caller %r attempted to act as disallowed role %r", principal.id, str(requested)
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"caller may not act as role '{requested}'",
        )
