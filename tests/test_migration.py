"""Sanity checks that the hand-written initial migration matches the ORM.

A full autogenerate-parity check needs a live PostgreSQL; these cheap checks
catch the most likely drift (missing table, enum value mismatch).
"""

import importlib.util
from pathlib import Path

from app.core import enums
from app.infra.models import Base

_path = Path(__file__).resolve().parents[1] / "alembic" / "versions" / "0001_initial.py"
_spec = importlib.util.spec_from_file_location("_migration_0001", _path)
migration = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(migration)


def test_all_orm_tables_are_in_metadata():
    assert set(Base.metadata.tables) == {
        "tasks",
        "capability_grants",
        "evidence",
        "audit_events",
    }


def test_enum_values_match_python_enums():
    m = migration._ENUMS
    assert set(m["agent_role"]) == {e.value for e in enums.AgentRole}
    assert set(m["risk_level"]) == {e.value for e in enums.RiskLevel}
    assert set(m["task_status"]) == {e.value for e in enums.TaskStatus}
    assert set(m["execution_mode"]) == {e.value for e in enums.ExecutionMode}
    assert set(m["budget_tier"]) == {e.value for e in enums.BudgetTier}
    assert set(m["truth_status"]) == {e.value for e in enums.TruthStatus}
    assert set(m["audit_outcome"]) == {e.value for e in enums.AuditOutcome}


def test_migration_has_single_head():
    assert migration.revision == "0001_initial"
    assert migration.down_revision is None
