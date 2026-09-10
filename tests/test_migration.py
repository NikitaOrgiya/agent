"""Sanity checks that the hand-written initial migration matches the ORM.

A full autogenerate-parity check needs a live PostgreSQL; these cheap checks
catch the most likely drift (missing table, enum value mismatch).
"""

import importlib.util
from pathlib import Path

from app.core import enums
from app.infra.models import Base

_VERSIONS = Path(__file__).resolve().parents[1] / "alembic" / "versions"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"_mig_{name}", _VERSIONS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


migration = _load("0001_initial")
migration2 = _load("0002_sprint2")


def test_all_orm_tables_are_in_metadata():
    assert set(Base.metadata.tables) == {
        "tasks",
        "capability_grants",
        "evidence",
        "audit_events",
        "model_calls",
        "conversations",
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


def test_migration_chain():
    assert migration.revision == "0001_initial"
    assert migration.down_revision is None
    assert migration2.revision == "0002_sprint2"
    assert migration2.down_revision == "0001_initial"
