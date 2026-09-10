import pytest

from app.core.enums import BudgetTier, ModelStatus
from app.core.model import ModelRequest, NullModelAdapter
from app.core.router import ModelRouter
from tests._fakes import FakeAdapter, answer, error

pytestmark = pytest.mark.asyncio


async def test_unavailable_fallback_is_default():
    r = ModelRouter()
    assert not r.has_available_model()
    resp = await r.generate(ModelRequest(prompt="hi"))
    assert resp.status is ModelStatus.MODEL_UNAVAILABLE


async def test_resolve_prefers_registered_profile():
    fake = FakeAdapter([answer("ok")])
    r = ModelRouter(retry_transient=False)
    r.register(BudgetTier.STRONG, fake)
    assert r.resolve(BudgetTier.STRONG) is fake
    assert isinstance(r.resolve(BudgetTier.ECONOMY), NullModelAdapter)  # falls to default


async def test_profiles_listing_has_no_credentials():
    fake = FakeAdapter([answer("ok")])
    r = ModelRouter()
    r.register(BudgetTier.STANDARD, fake)
    for p in r.profiles():
        d = p.public_dict()
        assert set(d) == {"provider", "model", "profile", "available", "context_window"}


async def test_single_retry_on_transient_error_then_success():
    fake = FakeAdapter([error("connection reset"), answer("recovered")])
    r = ModelRouter(retry_transient=True)
    r.register(BudgetTier.STANDARD, fake)
    resp = await r.generate(ModelRequest(prompt="hi", profile=BudgetTier.STANDARD))
    assert resp.status is ModelStatus.OK
    assert resp.text == "recovered"
    assert len(fake.calls) == 2


async def test_no_retry_on_auth_error():
    fake = FakeAdapter([error("model provider authentication failed")])
    r = ModelRouter(retry_transient=True)
    r.register(BudgetTier.STANDARD, fake)
    resp = await r.generate(ModelRequest(prompt="hi", profile=BudgetTier.STANDARD))
    assert resp.status is ModelStatus.MODEL_ERROR
    assert len(fake.calls) == 1


async def test_adapter_exception_becomes_model_error():
    class Boom(FakeAdapter):
        async def generate(self, request):  # type: ignore[override]
            raise RuntimeError("kaboom")

    r = ModelRouter(retry_transient=False)
    r.register(BudgetTier.STANDARD, Boom([answer("x")]))
    resp = await r.generate(ModelRequest(prompt="hi", profile=BudgetTier.STANDARD))
    assert resp.status is ModelStatus.MODEL_ERROR
