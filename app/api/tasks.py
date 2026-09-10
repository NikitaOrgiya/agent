from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.schemas import TaskCreate, TaskView
from app.core.task_service import create_task
from app.infra.db import get_session
from app.infra.models import Task

router = APIRouter(prefix="/v1/tasks", tags=["tasks"])


@router.post("", response_model=TaskView, status_code=201)
async def post_task(payload: TaskCreate, session: AsyncSession = Depends(get_session)):
    return await create_task(session, payload)


@router.get("/{task_id}", response_model=TaskView)
async def get_task(task_id: UUID, session: AsyncSession = Depends(get_session)):
    task = await session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task
