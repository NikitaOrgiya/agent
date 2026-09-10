from enum import StrEnum


class AgentRole(StrEnum):
    OWNER = "owner"
    COURIER = "courier"
    CUSTODIAN = "custodian"
    GUARDIAN = "guardian"
    LAB = "lab"
    RESEARCHER = "researcher"
    ENGINEER = "engineer"
    BROWSER = "browser"
    VERIFIER = "verifier"


class TaskStatus(StrEnum):
    RECEIVED = "received"
    CLARIFICATION_REQUIRED = "clarification_required"
    PLANNED = "planned"
    WAITING_APPROVAL = "waiting_approval"
    RUNNING = "running"
    VERIFYING = "verifying"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExecutionMode(StrEnum):
    PREVIEW = "preview"
    AUTONOMY = "autonomy"


class RiskLevel(StrEnum):
    L0 = "l0"
    L1 = "l1"
    L2 = "l2"
    L3 = "l3"
    L4 = "l4"


class BudgetTier(StrEnum):
    ECONOMY = "economy"
    STANDARD = "standard"
    STRONG = "strong"
    CRITICAL = "critical"


class PolicyDecision(StrEnum):
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"


class TruthStatus(StrEnum):
    OBSERVED = "observed"
    SUPPORTED = "supported"
    INFERRED = "inferred"
    UNCERTAIN = "uncertain"
    UNKNOWN = "unknown"
