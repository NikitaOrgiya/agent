from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.enums import AgentRole, BudgetTier, ExecutionMode, RiskLevel, TaskStatus, TruthStatus


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus), default=TaskStatus.RECEIVED)
    risk_level: Mapped[RiskLevel] = mapped_column(Enum(RiskLevel), default=RiskLevel.L0)
    requested_by: Mapped[str] = mapped_column(String(200))
    raw_input: Mapped[str] = mapped_column(Text)
    normalized_goal: Mapped[str | None] = mapped_column(Text, nullable=True)
    execution_mode: Mapped[ExecutionMode] = mapped_column(Enum(ExecutionMode))
    budget_tier: Mapped[BudgetTier] = mapped_column(Enum(BudgetTier))
    assigned_agent: Mapped[AgentRole | None] = mapped_column(Enum(AgentRole), nullable=True)
    result_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


class CapabilityGrant(Base):
    __tablename__ = "capability_grants"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    task_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("tasks.id"), nullable=True)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    actor: Mapped[AgentRole] = mapped_column(Enum(AgentRole))
    action: Mapped[str] = mapped_column(String(200))
    resource: Mapped[str] = mapped_column(String(500), default="*")
    scope: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    issued_by: Mapped[AgentRole] = mapped_column(Enum(AgentRole))
    max_calls: Mapped[int] = mapped_column(Integer, default=1)
    calls_used: Mapped[int] = mapped_column(Integer, default=0)
    revoked: Mapped[bool] = mapped_column(default=False)


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    task_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("tasks.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    claim: Mapped[str] = mapped_column(Text)
    truth_status: Mapped[TruthStatus] = mapped_column(Enum(TruthStatus))
    source_type: Mapped[str] = mapped_column(String(100))
    source_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    reliability: Mapped[float] = mapped_column(Float, default=0.5)
    extra: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    task_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("tasks.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    actor: Mapped[str] = mapped_column(String(200))
    action: Mapped[str] = mapped_column(String(200))
    decision: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
