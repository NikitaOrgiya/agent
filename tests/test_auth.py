"""API identity boundary for /v1/*."""

import pytest

from tests.conftest import TEST_CONTROL_TOKEN

pytestmark = pytest.mark.asyncio


async def test_health_needs_no_auth(client):
    assert (await client.get("/health")).status_code == 200


async def test_v1_requires_token(client):
    r = await client.post("/v1/tasks", json={"raw_input": "hello"})
    assert r.status_code == 401


async def test_v1_rejects_wrong_token(client):
    r = await client.post(
        "/v1/tasks", json={"raw_input": "hello"}, headers={"Authorization": "Bearer nope"}
    )
    assert r.status_code == 401


async def test_v1_accepts_valid_token(client, auth_headers):
    r = await client.post("/v1/tasks", json={"raw_input": "hello"}, headers=auth_headers)
    assert r.status_code == 202


async def test_caller_cannot_act_as_owner(client, auth_headers):
    r = await client.post(
        "/v1/tasks",
        json={"raw_input": "hello", "requested_actor": "owner"},
        headers=auth_headers,
    )
    assert r.status_code == 403


async def test_caller_cannot_act_as_custodian_on_policy(client, auth_headers):
    r = await client.post(
        "/v1/policy/check",
        json={"actor": "custodian", "action": "secret.read_raw", "resource": "secretref:db/main"},
        headers=auth_headers,
    )
    assert r.status_code == 403


async def test_no_token_configured_fails_closed(client, auth_headers, monkeypatch):
    from app.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setenv("AGENTOS_CONTROL_TOKEN", "")
    try:
        r = await client.post("/v1/tasks", json={"raw_input": "x"}, headers=auth_headers)
        assert r.status_code == 503
    finally:
        monkeypatch.setenv("AGENTOS_CONTROL_TOKEN", TEST_CONTROL_TOKEN)
        get_settings.cache_clear()
