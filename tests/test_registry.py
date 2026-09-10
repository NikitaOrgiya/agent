"""Capability registry security invariants."""

import re

from app.core.enums import AgentRole, RiskLevel
from app.core.registry import ACTION_REGISTRY

_CANON = re.compile(r"\A[a-z][a-z0-9]*(?:\.[a-z0-9][a-z0-9_]*)+\Z")
_RISK_ORDER = {r: i for i, r in enumerate(RiskLevel)}

_SECRET_MONEY_ROOT = ("secret.", "vault.", "wallet.", "payment.", "shell.", "device.root")
_DESTRUCTIVE = (".delete", ".destroy", ".wipe", ".drop", ".purge")


def test_all_action_names_are_canonical():
    for name, spec in ACTION_REGISTRY.items():
        assert name == spec.name
        assert _CANON.match(name), name


def test_lab_never_on_sensitive_actions():
    for name, spec in ACTION_REGISTRY.items():
        sensitive = name.startswith(_SECRET_MONEY_ROOT) or name.endswith(_DESTRUCTIVE)
        if sensitive:
            assert AgentRole.LAB not in spec.allowed_roles, name


def test_custodian_is_not_a_universal_executor():
    # Custodian may hold secret / capability actions, never business/destructive execution.
    for name in ("production.delete", "payment.execute"):
        assert AgentRole.CUSTODIAN not in ACTION_REGISTRY[name].allowed_roles


def test_sensitive_actions_have_high_min_risk():
    # secret.use_ref is deliberately lower risk: it never touches raw material.
    for name, spec in ACTION_REGISTRY.items():
        if name == "secret.use_ref":
            continue
        if name.startswith(_SECRET_MONEY_ROOT) or name.endswith(_DESTRUCTIVE):
            assert _RISK_ORDER[spec.min_risk] >= _RISK_ORDER[RiskLevel.L3], name


def test_every_spec_has_a_purpose():
    for spec in ACTION_REGISTRY.values():
        assert spec.purpose.strip()
        assert spec.allowed_roles  # non-empty
