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
    CREATED = "created"
    CLARIFYING = "clarifying"
    PLANNED = "planned"
    WAITING_APPROVAL = "waiting_approval"
    RUNNING = "running"
    COMPLETED = "completed"
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


class ModelStatus(StrEnum):
    OK = "ok"
    MODEL_UNAVAILABLE = "model_unavailable"
    MODEL_ERROR = "model_error"


class ModelResponseKind(StrEnum):
    """Whether a model turn is a usable answer or a request for more input."""

    ANSWER = "answer"
    NEEDS_CLARIFICATION = "needs_clarification"


class ConversationKind(StrEnum):
    COURIER = "courier"
    INTELLIGENCE = "intelligence"


class AuditOutcome(StrEnum):
    """What happened as a result of an audited attempt."""

    SUCCESS = "success"
    DENIED = "denied"
    APPROVAL_REQUIRED = "approval_required"
    ERROR = "error"
