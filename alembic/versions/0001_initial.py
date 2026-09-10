"""initial schema: tasks, capability_grants, evidence, audit_events

Revision ID: 0001_initial
Revises:
Create Date: 2026-09-10

PostgreSQL only. This project has one production database backend.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ENUMS: dict[str, tuple[str, ...]] = {
    "agent_role": (
        "owner",
        "courier",
        "custodian",
        "guardian",
        "lab",
        "researcher",
        "engineer",
        "browser",
        "verifier",
    ),
    "risk_level": ("l0", "l1", "l2", "l3", "l4"),
    "task_status": (
        "created",
        "clarifying",
        "planned",
        "waiting_approval",
        "running",
        "completed",
        "failed",
        "cancelled",
    ),
    "execution_mode": ("preview", "autonomy"),
    "budget_tier": ("economy", "standard", "strong", "critical"),
    "truth_status": ("observed", "supported", "inferred", "uncertain", "unknown"),
    "audit_outcome": ("success", "denied", "approval_required", "error"),
}


def _enum(name: str) -> postgresql.ENUM:
    return postgresql.ENUM(*_ENUMS[name], name=name, create_type=False)


def upgrade() -> None:
    for name, values in _ENUMS.items():
        joined = ", ".join(f"'{v}'" for v in values)
        op.execute(f"CREATE TYPE {name} AS ENUM ({joined})")

    op.create_table(
        "tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", _enum("task_status"), nullable=False),
        sa.Column("risk_level", _enum("risk_level"), nullable=False),
        sa.Column("caller", sa.String(length=200), nullable=False),
        sa.Column("requested_actor", _enum("agent_role"), nullable=True),
        sa.Column("assigned_role", _enum("agent_role"), nullable=True),
        sa.Column("raw_input", sa.Text(), nullable=False),
        sa.Column("normalized_goal", sa.Text(), nullable=True),
        sa.Column("execution_mode", _enum("execution_mode"), nullable=False),
        sa.Column("budget_tier", _enum("budget_tier"), nullable=False),
        sa.Column("result_summary", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
    )

    op.create_table(
        "capability_grants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "task_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tasks.id"),
            nullable=True,
        ),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor", _enum("agent_role"), nullable=False),
        sa.Column("action", sa.String(length=200), nullable=False),
        sa.Column("resource", sa.String(length=500), nullable=False),
        sa.Column("scope", sa.JSON(), nullable=True),
        sa.Column("issued_by", _enum("agent_role"), nullable=False),
        sa.Column("max_calls", sa.Integer(), nullable=False),
        sa.Column("calls_used", sa.Integer(), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False),
    )

    op.create_table(
        "evidence",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "task_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tasks.id"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("claim", sa.Text(), nullable=False),
        sa.Column("truth_status", _enum("truth_status"), nullable=False),
        sa.Column("source_type", sa.String(length=100), nullable=False),
        sa.Column("source_uri", sa.Text(), nullable=True),
        sa.Column("reliability", sa.Float(), nullable=False),
        sa.Column("extra", sa.JSON(), nullable=True),
    )

    op.create_table(
        "audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "task_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tasks.id"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor", sa.String(length=200), nullable=False),
        sa.Column("action", sa.String(length=200), nullable=False),
        sa.Column("resource", sa.String(length=500), nullable=True),
        sa.Column("decision", sa.String(length=50), nullable=True),
        sa.Column("outcome", _enum("audit_outcome"), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("extra", sa.JSON(), nullable=True),
    )
    op.create_index("ix_audit_events_created_at", "audit_events", ["created_at"])
    op.create_index("ix_audit_events_action", "audit_events", ["action"])


def downgrade() -> None:
    op.drop_index("ix_audit_events_action", table_name="audit_events")
    op.drop_index("ix_audit_events_created_at", table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_table("evidence")
    op.drop_table("capability_grants")
    op.drop_table("tasks")
    for name in reversed(list(_ENUMS)):
        op.execute(f"DROP TYPE {name}")
