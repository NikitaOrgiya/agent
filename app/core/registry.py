"""Central Capability / Action Registry.

Single source of truth for every action the Control Plane knows about. The
PolicyEngine reads role and risk metadata from here instead of keeping its own
parallel lists.

Design notes / invariants:

* This registry is an *allowlist*. An action absent from it is unknown, and an
  unknown action is denied by default (handled in the PolicyEngine).
* ``allowed_roles`` is who may *request* the action. It is still subject to the
  PolicyEngine's hard rules (LAB isolation, raw-secret boundary) and to the
  risk / approval gate.
* Custodian is a trusted SECRET / AUTHORIZATION boundary, not a universal
  executor. It appears here only for secret- and capability-related actions.
  Destructive or business actions (``production.delete``, ``payment.execute``)
  are assigned to an executor role (Engineer) and additionally require owner
  approval via the risk gate.
* LAB never appears on a secret / money / root / destructive action here, and
  the PolicyEngine enforces LAB isolation above the registry regardless.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.enums import AgentRole, RiskLevel

_ALL_ROLES: frozenset[AgentRole] = frozenset(AgentRole)


@dataclass(frozen=True)
class ActionSpec:
    name: str
    allowed_roles: frozenset[AgentRole]
    min_risk: RiskLevel
    purpose: str


def _spec(name: str, roles: set[AgentRole] | frozenset[AgentRole], min_risk: RiskLevel, purpose: str) -> ActionSpec:
    return ActionSpec(name=name, allowed_roles=frozenset(roles), min_risk=min_risk, purpose=purpose)


_SPECS: tuple[ActionSpec, ...] = (
    _spec(
        "policy.check",
        _ALL_ROLES,
        RiskLevel.L0,
        "Evaluate a capability request against the policy engine.",
    ),
    _spec(
        "task.create",
        {AgentRole.OWNER, AgentRole.COURIER},
        RiskLevel.L1,
        "Create a new task in the control plane.",
    ),
    _spec(
        "task.read",
        {AgentRole.OWNER, AgentRole.COURIER, AgentRole.GUARDIAN, AgentRole.LAB},
        RiskLevel.L1,
        "Read task state and metadata.",
    ),
    _spec(
        "reasoning.local",
        {
            AgentRole.LAB,
            AgentRole.RESEARCHER,
            AgentRole.ENGINEER,
            AgentRole.VERIFIER,
            AgentRole.COURIER,
            AgentRole.GUARDIAN,
        },
        RiskLevel.L0,
        "Local, model-free reasoning / analysis with no external effect.",
    ),
    _spec(
        "web.read_public",
        {AgentRole.LAB, AgentRole.RESEARCHER, AgentRole.BROWSER, AgentRole.COURIER},
        RiskLevel.L1,
        "Fetch public, read-only web content.",
    ),
    _spec(
        "evidence.read",
        {
            AgentRole.OWNER,
            AgentRole.COURIER,
            AgentRole.GUARDIAN,
            AgentRole.VERIFIER,
            AgentRole.LAB,
        },
        RiskLevel.L1,
        "Read stored evidence for a task.",
    ),
    _spec(
        "evidence.write",
        {AgentRole.COURIER, AgentRole.RESEARCHER, AgentRole.VERIFIER, AgentRole.GUARDIAN},
        RiskLevel.L2,
        "Attach evidence / observations to a task.",
    ),
    _spec(
        "secret.use_ref",
        {AgentRole.COURIER, AgentRole.ENGINEER, AgentRole.BROWSER, AgentRole.CUSTODIAN},
        RiskLevel.L2,
        "Use a SecretRef by identifier only; never exposes raw secret material.",
    ),
    _spec(
        "secret.read_raw",
        {AgentRole.CUSTODIAN},
        RiskLevel.L4,
        "Read raw secret material. Custodian boundary only; brokering preferred.",
    ),
    _spec(
        "vault.read",
        {AgentRole.CUSTODIAN},
        RiskLevel.L4,
        "Read an entry from the secret vault. Custodian boundary only.",
    ),
    _spec(
        "capability.issue",
        {AgentRole.CUSTODIAN, AgentRole.GUARDIAN},
        RiskLevel.L3,
        "Issue a scoped, expiring capability grant to another actor.",
    ),
    _spec(
        "production.delete",
        {AgentRole.ENGINEER},
        RiskLevel.L4,
        "Destructive production deletion. Executor role only, after owner "
        "approval and a dedicated capability grant.",
    ),
    _spec(
        "payment.execute",
        {AgentRole.ENGINEER},
        RiskLevel.L4,
        "Execute a payment. Executor role only, after owner approval and a "
        "dedicated capability grant.",
    ),
)

ACTION_REGISTRY: dict[str, ActionSpec] = {spec.name: spec for spec in _SPECS}


def get_action_spec(action: str) -> ActionSpec | None:
    return ACTION_REGISTRY.get(action)


def known_actions() -> frozenset[str]:
    return frozenset(ACTION_REGISTRY)
