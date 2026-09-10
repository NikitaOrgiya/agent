"""sprint 2: model_calls, conversations, tasks.pending_question

Revision ID: 0002_sprint2
Revises: 0001_initial
Create Date: 2026-09-10

PostgreSQL only.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_sprint2"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CONVERSATION_KIND = ("courier", "intelligence")


def upgrade() -> None:
    op.add_column("tasks", sa.Column("pending_question", sa.Text(), nullable=True))

    op.execute(
        "CREATE TYPE conversation_kind AS ENUM ("
        + ", ".join(f"'{v}'" for v in _CONVERSATION_KIND)
        + ")"
    )

    op.create_table(
        "model_calls",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "task_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tasks.id"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("provider", sa.String(length=60), nullable=False),
        sa.Column("model", sa.String(length=120), nullable=False),
        sa.Column("profile", sa.String(length=30), nullable=False),
        sa.Column("purpose", sa.String(length=60), nullable=False),
        sa.Column("prompt_version", sa.String(length=60), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("cost_usd", sa.Float(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
    )
    op.create_index("ix_model_calls_created_at", "model_calls", ["created_at"])
    op.create_index("ix_model_calls_task_id", "model_calls", ["task_id"])

    op.create_table(
        "conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("owner_key", sa.String(length=120), nullable=False),
        sa.Column(
            "kind",
            postgresql.ENUM(*_CONVERSATION_KIND, name="conversation_kind", create_type=False),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "active_task_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tasks.id"),
            nullable=True,
        ),
        sa.Column("model_profile", sa.String(length=30), nullable=True),
        sa.Column("turns", sa.JSON(), nullable=True),
    )
    op.create_index("ix_conversations_owner_key", "conversations", ["owner_key"])
    op.create_unique_constraint(
        "uq_conversations_owner_kind", "conversations", ["owner_key", "kind"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_conversations_owner_kind", "conversations", type_="unique")
    op.drop_index("ix_conversations_owner_key", table_name="conversations")
    op.drop_table("conversations")
    op.drop_index("ix_model_calls_task_id", table_name="model_calls")
    op.drop_index("ix_model_calls_created_at", table_name="model_calls")
    op.drop_table("model_calls")
    op.execute("DROP TYPE conversation_kind")
    op.drop_column("tasks", "pending_question")
