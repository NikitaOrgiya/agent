"""Courier domain service.

Courier solves a task on behalf of the system:

    owner message -> authenticate (at the gateway) -> Task -> ModelRouter ->
    model -> evidence + audit + model-call metadata -> Task complete -> reply

Telegram-specific code lives in ``app/telegram`` and never leaks in here.
Model output is untrusted text: it is never turned into a capability, and an
owner Telegram identity does not by itself grant any L3/L4 authority.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.context import ContextBuilder
from app.core.enums import (
    AgentRole,
    AuditOutcome,
    BudgetTier,
    ConversationKind,
    ModelResponseKind,
    ModelStatus,
    TaskStatus,
)
from app.core.model import ModelRequest
from app.core.router import ModelRouter
from app.core.system_contract import COURIER_CONTRACT_VERSION, COURIER_SYSTEM_CONTRACT
from app.services.audit import AuditService
from app.services.conversation import ConversationService
from app.services.evidence import EvidenceService
from app.services.model_calls import ModelCallService
from app.services.tasks import TaskService

logger = logging.getLogger("agentos.courier")

_MODEL_UNAVAILABLE_MESSAGE = (
    "I can't work on this yet: no model provider is connected (MODEL_UNAVAILABLE). "
    "Nothing was processed."
)
_GENERIC_ERROR_MESSAGE = (
    "Something went wrong while processing this and the task was marked failed. "
    "Please try again."
)


@dataclass(frozen=True)
class CourierCaller:
    id: str
    requested_actor: AgentRole


@dataclass(frozen=True)
class CourierSubmitResult:
    task_id: UUID
    status: str
    model_status: ModelStatus
    detail: str


@dataclass(frozen=True)
class CourierReply:
    text: str
    task_id: UUID
    status: TaskStatus
    model_status: ModelStatus


class CourierService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        router: ModelRouter | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.router = router or ModelRouter()
        self.tasks = TaskService(session)
        self.audit = AuditService(session)
        self.conversations = ConversationService(session)
        self.model_calls = ModelCallService(session)
        self.evidence = EvidenceService(session)
        self._context = ContextBuilder(
            max_messages=self.settings.context_max_messages,
            max_chars=self.settings.context_max_chars,
        )
        self._profile = BudgetTier(self.settings.default_model_profile.strip().lower())
        self._max_calls = self.settings.max_model_calls_per_task

    # --- HTTP path: create + report, no processing -----------------------
    async def submit(self, caller: CourierCaller, raw_input: str) -> CourierSubmitResult:
        task = await self.tasks.create(
            caller=caller.id, requested_actor=caller.requested_actor, raw_input=raw_input
        )
        await self.audit.record(
            actor=str(caller.requested_actor),
            action="task.create",
            resource=f"task:{task.id}",
            task_id=task.id,
            outcome=AuditOutcome.SUCCESS,
            reason="Task submitted through Courier (HTTP).",
            extra={"caller": caller.id, "raw_input_len": len(raw_input)},
        )
        available = self.router.has_available_model()
        return CourierSubmitResult(
            task_id=task.id,
            status=task.status,
            model_status=ModelStatus.OK if available else ModelStatus.MODEL_UNAVAILABLE,
            detail=(
                "Task accepted. Processing happens through the Telegram Courier."
                if available
                else "Task accepted and recorded, but no model provider is connected."
            ),
        )

    # --- Telegram path: full flow ------------------------------------
    async def handle_owner_message(self, owner_key: str, text: str) -> CourierReply:
        conv = await self.conversations.get_or_create(owner_key, ConversationKind.COURIER)

        task = None
        if conv.active_task_id is not None:
            candidate = await self.tasks.get(conv.active_task_id)
            if candidate is not None and candidate.status == TaskStatus.CLARIFYING:
                task = candidate

        if task is None:
            task = await self.tasks.create(
                caller=owner_key, requested_actor=AgentRole.COURIER, raw_input=text
            )
            await self.audit.record(
                actor="courier",
                action="task.create",
                resource=f"task:{task.id}",
                task_id=task.id,
                outcome=AuditOutcome.SUCCESS,
                reason="Task submitted via Telegram Courier.",
                extra={"owner": owner_key, "raw_input_len": len(text)},
            )
        else:
            base = task.normalized_goal or task.raw_input
            task.normalized_goal = f"{base}\n\nOwner clarification: {text}"[:16_000]

        history = self._context.build(self.conversations.turns(conv))
        await self.conversations.append_turn(conv, "user", text)

        # Model availability -> honest failure, not a fake answer.
        if not self.router.has_available_model():
            await self._fail(task, "model_unavailable")
            await self.conversations.set_active_task(conv, None)
            await self.audit.record(
                actor="courier",
                action="model.unavailable",
                resource=f"task:{task.id}",
                task_id=task.id,
                outcome=AuditOutcome.ERROR,
                reason="No model provider connected.",
            )
            await self.conversations.append_turn(conv, "assistant", _MODEL_UNAVAILABLE_MESSAGE)
            return CourierReply(_MODEL_UNAVAILABLE_MESSAGE, task.id, task.status, ModelStatus.MODEL_UNAVAILABLE)

        # Cost control: cap model calls per task.
        if await self.model_calls.count_for_task(task.id) >= self._max_calls:
            await self._fail(task, "model call budget exceeded")
            await self.conversations.set_active_task(conv, None)
            msg = "This task reached its model-call limit and was stopped."
            await self.conversations.append_turn(conv, "assistant", msg)
            return CourierReply(msg, task.id, task.status, ModelStatus.MODEL_ERROR)

        await self.tasks.transition(task, TaskStatus.RUNNING, assigned_role=AgentRole.COURIER)

        request = ModelRequest(
            prompt=text,
            system=COURIER_SYSTEM_CONTRACT,
            history=history,
            purpose="courier",
            profile=self._profile,
            prompt_version=COURIER_CONTRACT_VERSION,
        )
        response = await self.router.generate(request)
        await self.model_calls.record(response, task_id=task.id, purpose="courier")
        await self.audit.record(
            actor="courier",
            action="model.call",
            resource=f"task:{task.id}",
            task_id=task.id,
            outcome=AuditOutcome.SUCCESS if response.status is ModelStatus.OK else AuditOutcome.ERROR,
            reason=f"model call ({response.status})",
            extra={
                "provider": response.provider,
                "model": response.model,
                "profile": str(response.profile) if response.profile else None,
                "prompt_version": response.prompt_version,
                "latency_ms": response.latency_ms,
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
            },
        )

        if response.status is not ModelStatus.OK:
            await self._fail(task, response.error or "model error")
            await self.conversations.set_active_task(conv, None)
            await self.conversations.append_turn(conv, "assistant", _GENERIC_ERROR_MESSAGE)
            return CourierReply(_GENERIC_ERROR_MESSAGE, task.id, task.status, response.status)

        if response.kind is ModelResponseKind.NEEDS_CLARIFICATION:
            question = response.clarification_question or "Could you clarify your request?"
            await self.tasks.transition(task, TaskStatus.CLARIFYING, pending_question=question)
            await self.conversations.set_active_task(conv, task.id)
            await self.conversations.append_turn(conv, "assistant", question)
            return CourierReply(question, task.id, task.status, ModelStatus.OK)

        answer = response.text or ""
        await self.tasks.transition(
            task, TaskStatus.COMPLETED, result_summary=answer[:2000]
        )
        await self.evidence.record_model_answer(
            task_id=task.id,
            answer=answer,
            provider=response.provider,
            model=response.model,
            profile=str(response.profile) if response.profile else None,
            prompt_version=response.prompt_version,
        )
        await self.conversations.set_active_task(conv, None)
        await self.conversations.append_turn(conv, "assistant", answer)
        return CourierReply(answer, task.id, task.status, ModelStatus.OK)

    async def _fail(self, task, error: str) -> None:
        # created/clarifying/running -> failed are all valid transitions.
        try:
            await self.tasks.transition(task, TaskStatus.FAILED, error=error)
        except Exception:  # noqa: BLE001 - already terminal etc.; keep flow alive
            logger.warning("could not transition task %s to failed", task.id)
