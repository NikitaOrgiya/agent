"""Courier domain foundation (no Telegram, no LLM).

Responsibilities in Sprint 1:
    * accept an authenticated caller's request
    * create a Task
    * record the submission in the audit trail
    * report task id / status and the honest model status

It deliberately does NOT fabricate an AI answer. When no model is connected the
system says so (``MODEL_UNAVAILABLE``). The Model Adapter is injected, which is
the seam where a real provider is wired in a later sprint.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import AgentRole, AuditOutcome, ModelStatus
from app.core.model import ModelAdapter, NullModelAdapter
from app.services.audit import AuditService
from app.services.tasks import TaskService


@dataclass(frozen=True)
class CourierCaller:
    """The authenticated caller, distinct from the requested actor role."""

    id: str
    requested_actor: AgentRole


@dataclass(frozen=True)
class CourierSubmitResult:
    task_id: UUID
    status: str
    model_status: ModelStatus
    detail: str


class CourierService:
    def __init__(self, session: AsyncSession, model: ModelAdapter | None = None) -> None:
        self.session = session
        self.tasks = TaskService(session)
        self.audit = AuditService(session)
        self.model = model or NullModelAdapter()

    async def submit(self, caller: CourierCaller, raw_input: str) -> CourierSubmitResult:
        task = await self.tasks.create(
            caller=caller.id,
            requested_actor=caller.requested_actor,
            raw_input=raw_input,
        )
        await self.audit.record(
            actor=str(caller.requested_actor),
            action="task.create",
            resource=f"task:{task.id}",
            task_id=task.id,
            outcome=AuditOutcome.SUCCESS,
            reason="Task submitted through Courier.",
            extra={"caller": caller.id, "raw_input_len": len(raw_input)},
        )

        model_available = self.model.profile().available
        if model_available:
            detail = "Task accepted. Awaiting processing."
            model_status = ModelStatus.OK
        else:
            detail = (
                "Task accepted and recorded. Execution intelligence is not "
                "connected yet, so the task will not be processed until a model "
                "provider is wired in a later sprint."
            )
            model_status = ModelStatus.MODEL_UNAVAILABLE

        return CourierSubmitResult(
            task_id=task.id,
            status=task.status,
            model_status=model_status,
            detail=detail,
        )
