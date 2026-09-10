import pytest
from sqlalchemy import func, select

from app.core.enums import TaskStatus, TruthStatus
from app.infra.models import Evidence, ModelCall
from app.services.courier import CourierService
from tests._fakes import FakeAdapter, answer, clarify, error, router_with

pytestmark = pytest.mark.asyncio

OWNER = "telegram:5"


def _courier(session, adapter):
    return CourierService(session, router=router_with(adapter))


async def _count(session, model) -> int:
    return (await session.execute(select(func.count()).select_from(model))).scalar_one()


async def test_direct_answer_completes_task_with_inferred_evidence(session):
    svc = _courier(session, FakeAdapter([answer("The answer is 42.")]))
    reply = await svc.handle_owner_message(OWNER, "what is the meaning of life")
    assert reply.status == TaskStatus.COMPLETED
    assert reply.text == "The answer is 42."

    ev = (await session.execute(select(Evidence))).scalars().all()
    assert len(ev) == 1
    assert ev[0].truth_status == TruthStatus.INFERRED
    assert ev[0].source_type == "model"
    assert await _count(session, ModelCall) == 1


async def test_clarification_then_answer_uses_same_task(session):
    fake = FakeAdapter([clarify("Which language?"), answer("Hola.")])
    svc = _courier(session, fake)

    r1 = await svc.handle_owner_message(OWNER, "translate hello")
    assert r1.status == TaskStatus.CLARIFYING
    assert r1.text == "Which language?"

    r2 = await svc.handle_owner_message(OWNER, "spanish")
    assert r2.status == TaskStatus.COMPLETED
    assert r2.text == "Hola."
    assert r1.task_id == r2.task_id
    assert await _count(session, ModelCall) == 2


async def test_model_unavailable_fails_task_honestly(session):
    svc = _courier(session, FakeAdapter([answer("x")], available=False))
    reply = await svc.handle_owner_message(OWNER, "do something")
    assert reply.status == TaskStatus.FAILED
    assert "MODEL_UNAVAILABLE" in reply.text


async def test_model_error_fails_task_without_stack_trace(session):
    svc = _courier(session, FakeAdapter([error("model provider error (500)")]))
    reply = await svc.handle_owner_message(OWNER, "do something")
    assert reply.status == TaskStatus.FAILED
    assert "Traceback" not in reply.text
    assert "500" not in reply.text  # internal error text not forwarded verbatim


async def test_call_budget_stops_a_runaway_task(session):
    fake = FakeAdapter([clarify("q1"), clarify("q2"), answer("done")])
    svc = _courier(session, fake)
    await svc.handle_owner_message(OWNER, "start")          # call 1 -> clarifying
    await svc.handle_owner_message(OWNER, "more")           # call 2 -> clarifying
    r3 = await svc.handle_owner_message(OWNER, "even more")  # budget (2) reached
    assert r3.status == TaskStatus.FAILED
    assert await _count(session, ModelCall) == 2
