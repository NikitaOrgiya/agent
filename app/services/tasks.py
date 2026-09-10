"""Task lifecycle service.

Minimal, model-free. Enforces valid state transitions; an invalid transition is
rejected with ``InvalidTransition``.

    created -> clarifying | planned | running | waiting_approval | cancelled | failed
    clarifying -> planned | cancelled | failed
    planned -> running | waiting_approval | cancelled | failed
    waiting_approval -> running | planned | cancelled | failed
    running -> waiting_approval | completed | failed | cancelled
    completed / failed / cancelled -> (terminal)
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import AgentRole, TaskStatus
from app.infra.models import Task, utcnow

_TRANSITIONS: dict[TaskStatus, frozenset[TaskStatus]] = {
    TaskStatus.CREATED: frozenset(
        {
            TaskStatus.CLARIFYING,
            TaskStatus.PLANNED,
            TaskStatus.RUNNING,
            TaskStatus.WAITING_APPROVAL,
            TaskStatus.CANCELLED,
            TaskStatus.FAILED,
        }
    ),
    TaskStatus.CLARIFYING: frozenset(
        {TaskStatus.PLANNED, TaskStatus.CANCELLED, TaskStatus.FAILED}
    ),
    TaskStatus.PLANNED: frozenset(
        {
            TaskStatus.RUNNING,
            TaskStatus.WAITING_APPROVAL,
            TaskStatus.CANCELLED,
            TaskStatus.FAILED,
        }
    ),
    TaskStatus.WAITING_APPROVAL: frozenset(
        {
            TaskStatus.RUNNING,
            TaskStatus.PLANNED,
            TaskStatus.CANCELLED,
            TaskStatus.FAILED,
        }
    ),
    TaskStatus.RUNNING: frozenset(
        {
            TaskStatus.WAITING_APPROVAL,
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
        }
    ),
    TaskStatus.COMPLETED: frozenset(),
    TaskStatus.FAILED: frozenset(),
    TaskStatus.CANCELLED: frozenset(),
}

_TERMINAL: frozenset[TaskStatus] = frozenset(
    {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED}
)


class InvalidTransition(Exception):
    def __init__(self, current: TaskStatus, requested: TaskStatus) -> None:
        super().__init__(f"invalid task transition: {current} -> {requested}")
        self.current = current
        self.requested = requested


def allowed_transitions(current: TaskStatus) -> frozenset[TaskStatus]:
    return _TRANSITIONS.get(current, frozenset())


class TaskService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        caller: str,
        raw_input: str,
        requested_actor: AgentRole | None = None,
        normalized_goal: str | None = None,
    ) -> Task:
        task = Task(
            caller=caller,
            requested_actor=requested_actor,
            raw_input=raw_input,
            normalized_goal=normalized_goal,
            status=TaskStatus.CREATED,
        )
        self.session.add(task)
        await self.session.flush()
        return task

    async def get(self, task_id: UUID) -> Task | None:
        return await self.session.get(Task, task_id)

    async def transition(
        self,
        task: Task,
        new_status: TaskStatus,
        *,
        result_summary: str | None = None,
        error: str | None = None,
        assigned_role: AgentRole | None = None,
    ) -> Task:
        if new_status not in _TRANSITIONS.get(task.status, frozenset()):
            raise InvalidTransition(task.status, new_status)
        task.status = new_status
        task.updated_at = utcnow()
        if assigned_role is not None:
            task.assigned_role = assigned_role
        if result_summary is not None:
            task.result_summary = result_summary
        if error is not None:
            task.error = error
        if new_status in _TERMINAL:
            task.completed_at = utcnow()
        await self.session.flush()
        return task
