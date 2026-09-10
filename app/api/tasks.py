from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import Principal, authorize_actor, require_principal
from app.core.schemas import CourierRequestCreate, TaskAccepted, TaskView
from app.infra.db import get_session
from app.services.courier import CourierCaller, CourierService
from app.services.tasks import TaskService

router = APIRouter(prefix="/v1/tasks", tags=["tasks"])


@router.post("", response_model=TaskAccepted, status_code=status.HTTP_202_ACCEPTED)
async def submit_task(
    payload: CourierRequestCreate,
    principal: Principal = Depends(require_principal),
    session: AsyncSession = Depends(get_session),
) -> TaskAccepted:
    authorize_actor(principal, payload.requested_actor)
    caller = CourierCaller(id=principal.id, requested_actor=payload.requested_actor)
    try:
        result = await CourierService(session).submit(caller, payload.raw_input)
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    return TaskAccepted(
        task_id=result.task_id,
        status=result.status,
        model_status=result.model_status,
        detail=result.detail,
    )


@router.get("/{task_id}", response_model=TaskView)
async def get_task(
    task_id: UUID,
    principal: Principal = Depends(require_principal),
    session: AsyncSession = Depends(get_session),
) -> TaskView:
    task = await TaskService(session).get(task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")
    return task
