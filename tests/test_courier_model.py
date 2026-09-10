import pytest

from app.core.enums import AgentRole, ModelStatus, TaskStatus
from app.core.model import ModelRequest, NullModelAdapter
from app.services.courier import CourierCaller, CourierService

pytestmark = pytest.mark.asyncio


async def test_null_adapter_is_honest():
    adapter = NullModelAdapter()
    assert adapter.profile().available is False
    resp = await adapter.generate(ModelRequest(prompt="hello"))
    assert resp.status == ModelStatus.MODEL_UNAVAILABLE
    assert resp.text is None  # no fabricated answer
    assert resp.error  # explains why


async def test_courier_submit_creates_task_and_reports_unavailable(session):
    caller = CourierCaller(id="control-plane", requested_actor=AgentRole.COURIER)
    result = await CourierService(session).submit(caller, "please do X")
    assert result.status == TaskStatus.CREATED
    assert result.model_status == ModelStatus.MODEL_UNAVAILABLE
    assert "no model provider" in result.detail.lower()


async def test_courier_endpoint_reports_model_unavailable(client, auth_headers):
    r = await client.post("/v1/tasks", json={"raw_input": "hello"}, headers=auth_headers)
    assert r.status_code == 202
    body = r.json()
    assert body["model_status"] == "model_unavailable"
    assert body["status"] == "created"
