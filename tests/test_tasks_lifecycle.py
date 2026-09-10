import pytest

from app.core.enums import AgentRole, TaskStatus
from app.services.tasks import InvalidTransition, TaskService, allowed_transitions

pytestmark = pytest.mark.asyncio


async def _new_task(session) -> TaskService:
    svc = TaskService(session)
    task = await svc.create(caller="control-plane", requested_actor=AgentRole.COURIER, raw_input="x")
    return svc, task


async def test_task_starts_created(session):
    _, task = await _new_task(session)
    assert task.status == TaskStatus.CREATED
    assert task.completed_at is None


async def test_valid_transition_chain(session):
    svc, task = await _new_task(session)
    await svc.transition(task, TaskStatus.PLANNED)
    await svc.transition(task, TaskStatus.RUNNING, assigned_role=AgentRole.RESEARCHER)
    await svc.transition(task, TaskStatus.COMPLETED, result_summary="done")
    assert task.status == TaskStatus.COMPLETED
    assert task.assigned_role == AgentRole.RESEARCHER
    assert task.completed_at is not None


async def test_invalid_transition_rejected(session):
    svc, task = await _new_task(session)
    with pytest.raises(InvalidTransition):
        await svc.transition(task, TaskStatus.COMPLETED)  # created -> completed not allowed


async def test_terminal_state_is_dead_end(session):
    svc, task = await _new_task(session)
    await svc.transition(task, TaskStatus.CANCELLED)
    assert allowed_transitions(TaskStatus.CANCELLED) == frozenset()
    with pytest.raises(InvalidTransition):
        await svc.transition(task, TaskStatus.RUNNING)
