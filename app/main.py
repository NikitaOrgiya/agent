from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.policy import router as policy_router
from app.api.tasks import router as task_router
from app.infra.db import engine


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Database schema is managed by Alembic migrations, never by application
    # startup. Run `alembic upgrade head` before starting the service.
    yield
    await engine.dispose()


app = FastAPI(
    title="Agent OS Kernel",
    version="0.1.0",
    description="Security-first control plane for a personal multi-agent system.",
    lifespan=lifespan,
)

app.include_router(health_router)
app.include_router(task_router)
app.include_router(policy_router)
