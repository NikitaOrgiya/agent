"""Persistent audit trail.

Every security-important attempt is written to the ``audit_events`` table so it
can later be reconstructed: who, what operation, over which logical resource,
for which task, when, and with what result.

Fail-safe policy (see docs/AUDIT.md):
    The audit write shares the caller's DB transaction. If the audit write or
    the surrounding commit fails during a security-sensitive operation, the
    operation is NOT reported as successful -- the caller gets an error and the
    transaction is rolled back. A missing audit record never silently becomes a
    completed action.

Never pass raw secret values into ``extra`` / ``reason``. Obvious sensitive keys
are redacted defensively, but the contract is: callers do not put secrets here.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import AuditOutcome, PolicyDecision
from app.infra.models import AuditEvent

logger = logging.getLogger("agentos.audit")

_SENSITIVE_KEY_HINTS = ("secret", "token", "password", "passwd", "authorization", "api_key", "apikey")
_MAX_VALUE_LEN = 2000


def _redact(extra: dict[str, Any] | None) -> dict[str, Any]:
    if not extra:
        return {}
    clean: dict[str, Any] = {}
    for key, value in extra.items():
        key_str = str(key)
        if any(hint in key_str.lower() for hint in _SENSITIVE_KEY_HINTS):
            clean[key_str] = "[redacted]"
            continue
        text = value if isinstance(value, (int, float, bool)) or value is None else str(value)
        if isinstance(text, str) and len(text) > _MAX_VALUE_LEN:
            text = text[:_MAX_VALUE_LEN] + "...[truncated]"
        clean[key_str] = text
    return clean


_DECISION_TO_OUTCOME = {
    PolicyDecision.ALLOW: AuditOutcome.SUCCESS,
    PolicyDecision.DENY: AuditOutcome.DENIED,
    PolicyDecision.REQUIRE_APPROVAL: AuditOutcome.APPROVAL_REQUIRED,
}


def outcome_for_decision(decision: PolicyDecision) -> AuditOutcome:
    return _DECISION_TO_OUTCOME.get(decision, AuditOutcome.ERROR)


class AuditService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def record(
        self,
        *,
        actor: str,
        action: str,
        resource: str | None,
        outcome: AuditOutcome,
        task_id: UUID | None = None,
        decision: str | None = None,
        reason: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> AuditEvent:
        event = AuditEvent(
            task_id=task_id,
            actor=str(actor),
            action=action,
            resource=resource,
            decision=decision,
            outcome=outcome,
            reason=reason,
            extra=_redact(extra),
        )
        self.session.add(event)
        # flush (not commit): the caller owns the transaction boundary so that
        # audit and the security decision commit or roll back together.
        await self.session.flush()
        logger.info(
            "audit event recorded",
            extra={
                "actor": event.actor,
                "action": event.action,
                "resource": event.resource,
                "outcome": str(event.outcome),
                "task_id": str(event.task_id) if event.task_id else None,
            },
        )
        return event
