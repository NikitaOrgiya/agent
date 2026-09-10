from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.policy import router as policy_router
from app.api.tasks import router as task_router
from app.infra.db import engine
from app.infra.models import Base


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title="Agent OS Kernel",
    version="0.0.1",
    description="Security-first control plane for a personal multi-agent system.",
    lifespan=lifespan,
)

app.include_router(task_router)
app.include_router(policy_router)


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "agent-os-kernel"}
