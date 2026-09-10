from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.enums import (
    AgentRole,
    AuditOutcome,
    BudgetTier,
    ExecutionMode,
    RiskLevel,
    TaskStatus,
    TruthStatus,
)


def utcnow() -> datetime:
    return datetime.now(UTC)


# Explicit enum type names so Alembic migrations and the ORM stay in sync.
_ROLE = Enum(AgentRole, name="agent_role")
_RISK = Enum(RiskLevel, name="risk_level")
_TASK_STATUS = Enum(TaskStatus, name="task_status")
_EXEC_MODE = Enum(ExecutionMode, name="execution_mode")
_BUDGET = Enum(BudgetTier, name="budget_tier")
_TRUTH = Enum(TruthStatus, name="truth_status")
_OUTCOME = Enum(AuditOutcome, name="audit_outcome")


class Base(DeclarativeBase):
    pass


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    status: Mapped[TaskStatus] = mapped_column(_TASK_STATUS, default=TaskStatus.CREATED)
    risk_level: Mapped[RiskLevel] = mapped_column(_RISK, default=RiskLevel.L0)

    # Identity: the authenticated caller, and the role it asked to act as.
    caller: Mapped[str] = mapped_column(String(200))
    requested_actor: Mapped[AgentRole | None] = mapped_column(_ROLE, nullable=True)
    assigned_role: Mapped[AgentRole | None] = mapped_column(_ROLE, nullable=True)

    raw_input: Mapped[str] = mapped_column(Text)
    normalized_goal: Mapped[str | None] = mapped_column(Text, nullable=True)
    execution_mode: Mapped[ExecutionMode] = mapped_column(
        _EXEC_MODE, default=ExecutionMode.PREVIEW
    )
    budget_tier: Mapped[BudgetTier] = mapped_column(_BUDGET, default=BudgetTier.STANDARD)
    result_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


class CapabilityGrant(Base):
    __tablename__ = "capability_grants"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    task_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("tasks.id"), nullable=True
    )
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    actor: Mapped[AgentRole] = mapped_column(_ROLE)
    action: Mapped[str] = mapped_column(String(200))
    resource: Mapped[str] = mapped_column(String(500))
    scope: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    issued_by: Mapped[AgentRole] = mapped_column(_ROLE)
    max_calls: Mapped[int] = mapped_column(Integer, default=1)
    calls_used: Mapped[int] = mapped_column(Integer, default=0)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    task_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("tasks.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    claim: Mapped[str] = mapped_column(Text)
    truth_status: Mapped[TruthStatus] = mapped_column(_TRUTH)
    source_type: Mapped[str] = mapped_column(String(100))
    source_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    reliability: Mapped[float] = mapped_column(Float, default=0.5)
    extra: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    task_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("tasks.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    # who, over what logical resource, with what result
    actor: Mapped[str] = mapped_column(String(200))
    action: Mapped[str] = mapped_column(String(200))
    resource: Mapped[str | None] = mapped_column(String(500), nullable=True)
    decision: Mapped[str | None] = mapped_column(String(50), nullable=True)
    outcome: Mapped[AuditOutcome | None] = mapped_column(_OUTCOME, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
