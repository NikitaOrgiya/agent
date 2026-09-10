from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.enums import (
    AgentRole,
    BudgetTier,
    ExecutionMode,
    PolicyDecision,
    RiskLevel,
    TaskStatus,
    TruthStatus,
)


class TaskCreate(BaseModel):
    raw_input: str = Field(min_length=1, max_length=50_000)
    requested_by: str = "owner"
    execution_mode: ExecutionMode = ExecutionMode.PREVIEW
    budget_tier: BudgetTier = BudgetTier.STANDARD


class TaskView(BaseModel):
    id: UUID
    created_at: datetime
    updated_at: datetime
    status: TaskStatus
    risk_level: RiskLevel
    requested_by: str
    raw_input: str
    normalized_goal: str | None
    execution_mode: ExecutionMode
    budget_tier: BudgetTier
    assigned_agent: AgentRole | None
    result_summary: str | None
    error: str | None

    model_config = {"from_attributes": True}


class CapabilityRequest(BaseModel):
    task_id: UUID | None = None
    actor: AgentRole
    action: str = Field(min_length=1, max_length=200)
    # No wildcard default: a request must name a concrete resource. The policy
    # engine denies empty / "*" / malformed resources (deny by default).
    resource: str = Field(default="", max_length=500)
    risk_level: RiskLevel = RiskLevel.L1
    owner_approved: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class PolicyResult(BaseModel):
    decision: PolicyDecision
    reason: str
    matched_rule: str


class EvidenceCreate(BaseModel):
    task_id: UUID
    claim: str
    truth_status: TruthStatus
    source_type: str
    source_uri: str | None = None
    reliability: float = Field(default=0.5, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)
