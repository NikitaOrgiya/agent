"""Test fixtures.

The database used in tests is in-memory SQLite via aiosqlite. This is a TEST
CONVENIENCE ONLY. PostgreSQL is the sole production backend; schema in
production is managed by Alembic migrations, not by ``create_all``.
"""

from __future__ import annotations

import os

import pytest
import pytest_asyncio

os.environ.setdefault("AGENTOS_ENV", "test")
os.environ.setdefault("AGENTOS_CONTROL_TOKEN", "test-control-token-1234567890")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.infra.models import Base

TEST_CONTROL_TOKEN = os.environ["AGENTOS_CONTROL_TOKEN"]


@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def sessionmaker(engine):
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest_asyncio.fixture
async def session(sessionmaker):
    async with sessionmaker() as s:
        yield s


@pytest_asyncio.fixture
async def client(sessionmaker):
    from httpx import ASGITransport, AsyncClient

    from app.infra.db import get_session
    from app.main import app

    async def _override_get_session():
        async with sessionmaker() as s:
            yield s

    app.dependency_overrides[get_session] = _override_get_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers():
    return {"Authorization": f"Bearer {TEST_CONTROL_TOKEN}"}
