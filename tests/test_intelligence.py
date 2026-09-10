import pytest

from app.core.enums import ModelStatus
from app.core.router import ModelRouter
from app.services.intelligence import IntelligenceService
from tests._fakes import FakeAdapter, answer, router_with

pytestmark = pytest.mark.asyncio

OWNER = "telegram:7"


async def test_intelligence_unavailable_is_honest(session):
    svc = IntelligenceService(session, router=ModelRouter())
    reply = await svc.handle_message(OWNER, "hello")
    assert reply.model_status is ModelStatus.MODEL_UNAVAILABLE
    assert "MODEL_UNAVAILABLE" in reply.text


async def test_intelligence_direct_answer_and_memory(session):
    fake = FakeAdapter([answer("first"), answer("second")])
    svc = IntelligenceService(session, router=router_with(fake))
    r1 = await svc.handle_message(OWNER, "one")
    r2 = await svc.handle_message(OWNER, "two")
    assert r1.text == "first"
    assert r2.text == "second"
    # second call carries the prior turns as history
    assert len(fake.calls[1].history) >= 2


async def test_models_listing_and_switch(session):
    fake = FakeAdapter([answer("x")])
    svc = IntelligenceService(session, router=router_with(fake))
    listing = await svc.list_models()
    assert any(m["available"] for m in listing)
    assert all("api_key" not in m and "base_url" not in m for m in listing)

    ok, msg = await svc.set_model(OWNER, "strong")
    assert ok and "strong" in msg
    assert await svc.current_model(OWNER) == "strong"

    bad_ok, _ = await svc.set_model(OWNER, "nonsense-profile")
    assert bad_ok is False


async def test_new_clears_conversation(session):
    fake = FakeAdapter([answer("a"), answer("b")])
    svc = IntelligenceService(session, router=router_with(fake))
    await svc.handle_message(OWNER, "remember this")
    await svc.reset(OWNER)
    await svc.handle_message(OWNER, "fresh start")
    assert len(fake.calls[-1].history) == 0
