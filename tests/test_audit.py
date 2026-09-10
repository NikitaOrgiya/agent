"""Persistent audit trail."""

import pytest
from sqlalchemy import func, select

from app.core.enums import AgentRole, AuditOutcome
from app.infra.models import AuditEvent
from app.services.audit import AuditService

pytestmark = pytest.mark.asyncio


async def _count(session) -> int:
    return (await session.execute(select(func.count()).select_from(AuditEvent))).scalar_one()


async def test_policy_check_is_persisted(client, auth_headers, session):
    r = await client.post(
        "/v1/policy/check",
        json={"actor": "researcher", "action": "web.read_public", "resource": "service:example"},
        headers=auth_headers,
    )
    assert r.status_code == 200
    rows = (await session.execute(select(AuditEvent))).scalars().all()
    assert len(rows) == 1
    ev = rows[0]
    assert ev.actor == "researcher"
    assert ev.action == "web.read_public"
    assert ev.resource == "service:example"
    assert ev.outcome == AuditOutcome.SUCCESS
    assert ev.decision == "allow"


async def test_task_submission_is_persisted(client, auth_headers, session):
    r = await client.post("/v1/tasks", json={"raw_input": "do a thing"}, headers=auth_headers)
    assert r.status_code == 202
    rows = (await session.execute(select(AuditEvent).where(AuditEvent.action == "task.create"))).scalars().all()
    assert len(rows) == 1
    assert rows[0].task_id is not None


async def test_audit_redacts_sensitive_keys(session):
    audit = AuditService(session)
    ev = await audit.record(
        actor=str(AgentRole.COURIER),
        action="reasoning.local",
        resource="local:reasoning",
        outcome=AuditOutcome.SUCCESS,
        extra={"api_token": "super-secret-value", "note": "ok"},
    )
    assert ev.extra["api_token"] == "[redacted]"
    assert ev.extra["note"] == "ok"


async def test_audit_failure_fails_closed(client, auth_headers, monkeypatch):
    async def boom(*_a, **_k):
        raise RuntimeError("db down")

    monkeypatch.setattr(AuditService, "record", boom)
    r = await client.post(
        "/v1/policy/check",
        json={"actor": "researcher", "action": "web.read_public", "resource": "service:example"},
        headers=auth_headers,
    )
    assert r.status_code == 503
