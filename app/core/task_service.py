from sqlalchemy.ext.asyncio import AsyncSession

from app.core.schemas import TaskCreate
from app.infra.models import AuditEvent, Task


async def create_task(session: AsyncSession, payload: TaskCreate) -> Task:
    task = Task(
        requested_by=payload.requested_by,
        raw_input=payload.raw_input,
        execution_mode=payload.execution_mode,
        budget_tier=payload.budget_tier,
    )
    session.add(task)
    await session.flush()

    session.add(
        AuditEvent(
            task_id=task.id,
            actor=payload.requested_by,
            action="task.created",
            extra={"execution_mode": payload.execution_mode, "budget_tier": payload.budget_tier},
        )
    )
    await session.commit()
    await session.refresh(task)
    return task
