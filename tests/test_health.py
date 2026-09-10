import pytest

pytestmark = pytest.mark.asyncio


async def test_health_ok(client):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


async def test_readiness_ok_with_database(client):
    r = await client.get("/readiness")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ready"
    assert body["checks"]["database"] == "ok"


async def test_health_leaks_no_secrets(client):
    r = await client.get("/health")
    assert "password" not in r.text.lower()
    assert "postgresql://" not in r.text
