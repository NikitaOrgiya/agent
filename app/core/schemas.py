from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.enums import (
    AgentRole,
    BudgetTier,
    ExecutionMode,
    ModelStatus,
    PolicyDecision,
    RiskLevel,
    TaskStatus,
    TruthStatus,
)


class CourierRequestCreate(BaseModel):
    """A request submitted by an authenticated caller through the Courier."""

    raw_input: str = Field(min_length=1, max_length=50_000)
    # The role the caller asks to act as. The auth layer decides whether the
    # caller is allowed to request this role; it is never trusted from JSON alone.
    requested_actor: AgentRole = AgentRole.COURIER
    execution_mode: ExecutionMode = ExecutionMode.PREVIEW
    budget_tier: BudgetTier = BudgetTier.STANDARD


class TaskAccepted(BaseModel):
    task_id: UUID
    status: TaskStatus
    model_status: ModelStatus
    detail: str


class TaskView(BaseModel):
    id: UUID
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    status: TaskStatus
    risk_level: RiskLevel
    caller: str
    requested_actor: AgentRole | None
    assigned_role: AgentRole | None
    raw_input: str
    normalized_goal: str | None
    execution_mode: ExecutionMode
    budget_tier: BudgetTier
    result_summary: str | None
    error: str | None

    model_config = {"from_attributes": True}


class CapabilityRequest(BaseModel):
    task_id: UUID | None = None
    # The role for which the capability is requested (not proven identity).
    actor: AgentRole
    action: str = Field(min_length=1, max_length=200)
    # Canonical logical ResourceId ("type:value"); the policy engine denies
    # empty / "*" / malformed resources (deny by default).
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
