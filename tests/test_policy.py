"""Trust-boundary tests for the deterministic policy engine.

Every test here encodes a security invariant. The engine is deny-by-default:
anything not explicitly allowed, well-formed, and within its risk budget must
resolve to DENY or REQUIRE_APPROVAL.
"""

import pytest

from app.core.enums import AgentRole, PolicyDecision, RiskLevel
from app.core.policy import PolicyEngine
from app.core.schemas import CapabilityRequest

engine = PolicyEngine()


def _req(**kwargs) -> CapabilityRequest:
    base = dict(actor=AgentRole.COURIER, action="reasoning.local", resource="local")
    base.update(kwargs)
    return CapabilityRequest(**base)


# --- 1. unknown action -> denied ------------------------------------------------
def test_unknown_action_denied():
    result = engine.check(_req(actor=AgentRole.COURIER, action="totally.unknown.capability"))
    assert result.decision == PolicyDecision.DENY
    assert result.matched_rule == "NO_MATCHING_ALLOW_RULE"


# --- 2. unknown / unspecified / wildcard resource -> denied --------------------
def test_missing_resource_denied():
    result = engine.check(
        CapabilityRequest(actor=AgentRole.COURIER, action="reasoning.local")
    )
    assert result.decision == PolicyDecision.DENY
    assert result.matched_rule == "MALFORMED_RESOURCE"


def test_wildcard_resource_denied():
    result = engine.check(_req(resource="*"))
    assert result.decision == PolicyDecision.DENY
    assert result.matched_rule == "MALFORMED_RESOURCE"


def test_path_traversal_resource_denied():
    result = engine.check(_req(resource="../../etc/passwd"))
    assert result.decision == PolicyDecision.DENY
    assert result.matched_rule == "MALFORMED_RESOURCE"


# --- 3. LAB -> secret denied --------------------------------------------------
def test_lab_cannot_read_secrets():
    result = engine.check(
        _req(actor=AgentRole.LAB, action="secret.read_raw", resource="secret://db", risk_level=RiskLevel.L1)
    )
    assert result.decision == PolicyDecision.DENY
    assert result.matched_rule == "LAB_HARD_ISOLATION"


def test_lab_cannot_use_secret_ref_either():
    # secret.use_ref is allow-listed for Courier/Custodian/Engineer/Browser, not LAB.
    result = engine.check(
        _req(actor=AgentRole.LAB, action="secret.use_ref", resource="secret://api-key")
    )
    assert result.decision == PolicyDecision.DENY
    assert result.matched_rule == "LAB_HARD_ISOLATION"


# --- 4. LAB -> privileged / destructive action denied -------------------------
@pytest.mark.parametrize(
    "action",
    ["wallet.transfer", "payment.send", "device.root", "shell.exec", "production.delete", "database.drop"],
)
def test_lab_privileged_and_destructive_denied(action):
    result = engine.check(_req(actor=AgentRole.LAB, action=action, resource="prod/main"))
    assert result.decision == PolicyDecision.DENY
    assert result.matched_rule == "LAB_HARD_ISOLATION"


# --- 5. Courier -> raw secret denied -----------------------------------------
def test_courier_cannot_read_raw_secret():
    result = engine.check(
        _req(actor=AgentRole.COURIER, action="secret.read_raw", resource="secret://db")
    )
    assert result.decision == PolicyDecision.DENY
    assert result.matched_rule == "COURIER_NO_RAW_SECRETS"


@pytest.mark.parametrize("action", ["vault.export", "secret.reveal", "secret.export"])
def test_courier_cannot_exfiltrate_secret_material(action):
    result = engine.check(_req(actor=AgentRole.COURIER, action=action, resource="secret://db"))
    assert result.decision == PolicyDecision.DENY


def test_non_custodian_cannot_read_raw_secret():
    for role in (AgentRole.RESEARCHER, AgentRole.ENGINEER, AgentRole.GUARDIAN, AgentRole.BROWSER):
        result = engine.check(_req(actor=role, action="secret.read_raw", resource="secret://db"))
        assert result.decision == PolicyDecision.DENY
        assert result.matched_rule == "SECRET_MATERIAL_CUSTODIAN_ONLY"


# --- 6. L4 without owner approval -> denied (require approval) ----------------
def test_l4_always_needs_owner_approval():
    result = engine.check(
        _req(actor=AgentRole.CUSTODIAN, action="production.delete", resource="prod/db-main", risk_level=RiskLevel.L4)
    )
    assert result.decision == PolicyDecision.REQUIRE_APPROVAL
    assert result.matched_rule == "L4_OWNER_APPROVAL"
    assert result.decision != PolicyDecision.ALLOW


def test_l4_risk_cannot_be_under_declared():
    # Caller claims L1 for a destructive action; the engine raises the floor to L4.
    result = engine.check(
        _req(actor=AgentRole.CUSTODIAN, action="production.delete", resource="prod/db-main", risk_level=RiskLevel.L1)
    )
    assert result.decision == PolicyDecision.REQUIRE_APPROVAL
    assert result.matched_rule == "L4_OWNER_APPROVAL"


def test_money_movement_requires_owner_approval():
    result = engine.check(
        _req(actor=AgentRole.CUSTODIAN, action="wallet.transfer", resource="wallet/main", risk_level=RiskLevel.L2)
    )
    assert result.decision == PolicyDecision.REQUIRE_APPROVAL


# --- 7. malformed capability -> denied --------------------------------------
def _raw(**kwargs) -> CapabilityRequest:
    """Build a request bypassing pydantic validation, to exercise the engine's
    own input validation against payloads a hostile / buggy caller might send."""
    base = dict(
        actor=AgentRole.COURIER, action="reasoning.local", resource="local",
        risk_level=RiskLevel.L1, owner_approved=False, metadata={}, task_id=None,
    )
    base.update(kwargs)
    return CapabilityRequest.model_construct(**base)


@pytest.mark.parametrize(
    "action",
    ["", "   ", "UPPER.CASE", "no-dot", "secret..double", ".leading", "trailing.",
     "bad name", "inject;drop", "wild*card"],
)
def test_malformed_action_denied(action):
    result = engine.check(_raw(action=action, resource="local"))
    assert result.decision == PolicyDecision.DENY
    assert result.matched_rule == "MALFORMED_ACTION"


def test_case_trick_does_not_bypass_isolation():
    # "SECRET.Read_Raw" must not slip past the LAB isolation / secret rules.
    result = engine.check(_raw(actor=AgentRole.LAB, action="SECRET.Read_Raw", resource="secret://db"))
    assert result.decision == PolicyDecision.DENY
    assert result.matched_rule in {"MALFORMED_ACTION", "LAB_HARD_ISOLATION"}


def test_whitespace_padding_does_not_bypass():
    result = engine.check(_raw(actor=AgentRole.COURIER, action="  secret.read_raw  ", resource="secret://db"))
    assert result.decision == PolicyDecision.DENY
    assert result.matched_rule in {"MALFORMED_ACTION", "COURIER_NO_RAW_SECRETS"}


def test_non_string_action_denied():
    result = engine.check(_raw(actor=AgentRole.COURIER, action=None, resource="local"))
    assert result.decision == PolicyDecision.DENY
    assert result.matched_rule == "MALFORMED_ACTION"


# --- 8. policy evaluation failure -> denied (fail closed) --------------------
def test_evaluation_error_fails_closed(monkeypatch):
    def boom(*_args, **_kwargs):
        raise RuntimeError("simulated internal failure")

    monkeypatch.setattr(PolicyEngine, "_match_allow_rule", boom)
    result = engine.check(_req(actor=AgentRole.COURIER, action="reasoning.local", resource="local"))
    assert result.decision == PolicyDecision.DENY
    assert result.matched_rule == "EVALUATION_ERROR"


# --- 9. an explicitly allowed safe action still works -----------------------
def test_allowed_safe_action_still_allowed():
    result = engine.check(
        _req(actor=AgentRole.COURIER, action="reasoning.local", resource="local", risk_level=RiskLevel.L0)
    )
    assert result.decision == PolicyDecision.ALLOW
    assert result.matched_rule == "EXPLICIT_ALLOW"


def test_public_web_read_allowed():
    result = engine.check(
        _req(actor=AgentRole.RESEARCHER, action="web.read_public", resource="https:example.com", risk_level=RiskLevel.L0)
    )
    assert result.decision == PolicyDecision.ALLOW


def test_l4_owner_approved_can_pass_policy():
    result = engine.check(
        _req(
            actor=AgentRole.CUSTODIAN,
            action="production.delete",
            resource="prod/db-main",
            risk_level=RiskLevel.L4,
            owner_approved=True,
        )
    )
    assert result.decision == PolicyDecision.ALLOW


def test_role_not_in_allowlist_denied():
    # Researcher is not permitted to create tasks.
    result = engine.check(
        _req(actor=AgentRole.RESEARCHER, action="task.create", resource="task/new")
    )
    assert result.decision == PolicyDecision.DENY
    assert result.matched_rule == "ROLE_NOT_PERMITTED"
