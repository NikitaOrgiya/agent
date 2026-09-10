"""PolicyEngine trust-boundary tests (deny-by-default, registry-backed)."""

import pytest

from app.core.enums import AgentRole, PolicyDecision, RiskLevel
from app.core.policy import PolicyEngine
from app.core.schemas import CapabilityRequest

engine = PolicyEngine()


def _req(**kw) -> CapabilityRequest:
    base = dict(actor=AgentRole.COURIER, action="reasoning.local", resource="local:reasoning")
    base.update(kw)
    return CapabilityRequest(**base)


def _raw(**kw) -> CapabilityRequest:
    base = dict(
        actor=AgentRole.COURIER, action="reasoning.local", resource="local:reasoning",
        risk_level=RiskLevel.L1, owner_approved=False, metadata={}, task_id=None,
    )
    base.update(kw)
    return CapabilityRequest.model_construct(**base)


# 1. unknown action -> deny
def test_unknown_action_denied():
    r = engine.check(_req(action="totally.unknown"))
    assert r.decision == PolicyDecision.DENY
    assert r.matched_rule == "UNKNOWN_ACTION"


# 2. unknown / malformed / wildcard resource -> deny
@pytest.mark.parametrize("resource", ["", "*", "local:*", "../etc", "LOCAL:reasoning", "noscheme", "secretref:"])
def test_bad_resource_denied(resource):
    r = engine.check(_raw(resource=resource))
    assert r.decision == PolicyDecision.DENY
    assert r.matched_rule == "MALFORMED_RESOURCE"


# 3. LAB -> secret denied
def test_lab_secret_denied():
    r = engine.check(_req(actor=AgentRole.LAB, action="secret.read_raw", resource="secretref:db/main"))
    assert r.decision == PolicyDecision.DENY
    assert r.matched_rule == "LAB_HARD_ISOLATION"


# 4. LAB -> privileged / destructive denied
@pytest.mark.parametrize("action", ["wallet.transfer", "payment.execute", "device.root", "shell.exec", "production.delete", "db.drop"])
def test_lab_privileged_denied(action):
    r = engine.check(_req(actor=AgentRole.LAB, action=action, resource="service:prod"))
    assert r.decision == PolicyDecision.DENY
    assert r.matched_rule == "LAB_HARD_ISOLATION"


# 5. Courier -> raw secret denied
def test_courier_raw_secret_denied():
    r = engine.check(_req(actor=AgentRole.COURIER, action="secret.read_raw", resource="secretref:db/main"))
    assert r.decision == PolicyDecision.DENY
    assert r.matched_rule == "COURIER_NO_RAW_SECRETS"


def test_non_custodian_raw_secret_denied():
    for role in (AgentRole.ENGINEER, AgentRole.RESEARCHER, AgentRole.GUARDIAN, AgentRole.BROWSER):
        r = engine.check(_req(actor=role, action="secret.read_raw", resource="secretref:db/main"))
        assert r.decision == PolicyDecision.DENY
        assert r.matched_rule == "SECRET_MATERIAL_CUSTODIAN_ONLY"


# 6. L4 without owner approval -> require approval (never allow)
def test_l4_requires_owner_approval():
    r = engine.check(_req(actor=AgentRole.CUSTODIAN, action="secret.read_raw",
                          resource="secretref:db/main", risk_level=RiskLevel.L4))
    assert r.decision == PolicyDecision.REQUIRE_APPROVAL
    assert r.matched_rule == "L4_OWNER_APPROVAL"


def test_risk_cannot_be_under_declared():
    # caller claims L0 for an L4 registry action -> engine raises the floor
    r = engine.check(_req(actor=AgentRole.CUSTODIAN, action="secret.read_raw",
                          resource="secretref:db/main", risk_level=RiskLevel.L0))
    assert r.decision == PolicyDecision.REQUIRE_APPROVAL
    assert r.matched_rule == "L4_OWNER_APPROVAL"


# 7. malformed action -> deny
@pytest.mark.parametrize("action", ["", "  ", "UPPER.CASE", "nodot", "a..b", ".x", "x.", "bad name", "wild*"])
def test_malformed_action_denied(action):
    r = engine.check(_raw(action=action))
    assert r.decision == PolicyDecision.DENY
    assert r.matched_rule == "MALFORMED_ACTION"


# 8. evaluation failure -> deny (fail closed)
def test_evaluation_error_fails_closed(monkeypatch):
    def boom(*_a, **_k):
        raise RuntimeError("boom")

    monkeypatch.setattr(PolicyEngine, "_effective_risk", boom)
    r = engine.check(_req(action="reasoning.local", resource="local:reasoning"))
    assert r.decision == PolicyDecision.DENY
    assert r.matched_rule == "EVALUATION_ERROR"


# 9. an allowed safe action still works
def test_allowed_action_still_allowed():
    r = engine.check(_req(actor=AgentRole.RESEARCHER, action="web.read_public",
                          resource="service:example", risk_level=RiskLevel.L1))
    assert r.decision == PolicyDecision.ALLOW
    assert r.matched_rule == "REGISTRY_ALLOW"


# corrected invariant: Custodian is NOT a universal executor
def test_custodian_cannot_execute_production_delete():
    r = engine.check(_req(actor=AgentRole.CUSTODIAN, action="production.delete",
                          resource="service:prod-db", risk_level=RiskLevel.L4, owner_approved=True))
    assert r.decision == PolicyDecision.DENY
    assert r.matched_rule == "ROLE_NOT_PERMITTED"


def test_engineer_executes_production_delete_with_owner_approval():
    r = engine.check(_req(actor=AgentRole.ENGINEER, action="production.delete",
                          resource="service:prod-db", risk_level=RiskLevel.L4, owner_approved=True))
    assert r.decision == PolicyDecision.ALLOW


def test_engineer_production_delete_without_approval_blocked():
    r = engine.check(_req(actor=AgentRole.ENGINEER, action="production.delete",
                          resource="service:prod-db", risk_level=RiskLevel.L4))
    assert r.decision == PolicyDecision.REQUIRE_APPROVAL


def test_role_not_permitted_for_registered_action():
    r = engine.check(_req(actor=AgentRole.RESEARCHER, action="task.create", resource="task:abc123"))
    assert r.decision == PolicyDecision.DENY
    assert r.matched_rule == "ROLE_NOT_PERMITTED"
