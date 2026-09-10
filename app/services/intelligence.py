"""Intelligence Zone service.

A direct owner <-> model conversation. NOT routed through the Courier planner,
task lifecycle, or evidence pipeline.

Boundaries (enforced structurally -- this service only ever calls a model and
returns text):
    * no secrets, no Vault, no device authority, no production actions
    * no capability requests at all -> nothing here can reach a PolicyEngine ALLOW
    * model output is untrusted text and never becomes an action

Intellectual freedom != authority.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.context import ContextBuilder
from app.core.enums import AuditOutcome, BudgetTier, ConversationKind, ModelStatus
from app.core.model import ModelRequest
from app.core.router import ModelRouter
from app.core.system_contract import INTELLIGENCE_CONTRACT_VERSION, INTELLIGENCE_SYSTEM_CONTRACT
from app.services.audit import AuditService
from app.services.conversation import ConversationService
from app.services.model_calls import ModelCallService

logger = logging.getLogger("agentos.intelligence")

_VALID_PROFILES = {t.value for t in BudgetTier}
_MODEL_UNAVAILABLE = (
    "No model provider is connected (MODEL_UNAVAILABLE). Set MODEL_PROVIDER and "
    "the matching API key."
)


@dataclass(frozen=True)
class IntelligenceReply:
    text: str
    model_status: ModelStatus
    profile: str


class IntelligenceService:
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
        self.audit = AuditService(session)
        self.conversations = ConversationService(session)
        self.model_calls = ModelCallService(session)
        self._context = ContextBuilder(
            max_messages=self.settings.context_max_messages,
            max_chars=self.settings.context_max_chars,
        )
        self._default_profile = self.settings.default_model_profile.strip().lower()

    async def _conv(self, owner_key: str):
        return await self.conversations.get_or_create(owner_key, ConversationKind.INTELLIGENCE)

    def _profile_for(self, conv) -> BudgetTier:
        raw = (conv.model_profile or self._default_profile).strip().lower()
        return BudgetTier(raw) if raw in _VALID_PROFILES else BudgetTier(self._default_profile)

    async def handle_message(self, owner_key: str, text: str) -> IntelligenceReply:
        conv = await self._conv(owner_key)
        profile = self._profile_for(conv)

        if not self.router.has_available_model():
            return IntelligenceReply(_MODEL_UNAVAILABLE, ModelStatus.MODEL_UNAVAILABLE, str(profile))

        history = self._context.build(self.conversations.turns(conv))
        await self.conversations.append_turn(conv, "user", text)

        request = ModelRequest(
            prompt=text,
            system=INTELLIGENCE_SYSTEM_CONTRACT,
            history=history,
            purpose="intelligence",
            profile=profile,
            prompt_version=INTELLIGENCE_CONTRACT_VERSION,
        )
        response = await self.router.generate(request)
        await self.model_calls.record(response, task_id=None, purpose="intelligence")
        await self.audit.record(
            actor="lab",
            action="model.call",
            resource=f"intelligence:{owner_key}",
            outcome=AuditOutcome.SUCCESS if response.status is ModelStatus.OK else AuditOutcome.ERROR,
            reason=f"intelligence-zone model call ({response.status})",
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
            return IntelligenceReply(
                "The model call failed. Please try again.", response.status, str(profile)
            )

        # Intelligence Zone does not gate on clarification; return the raw reply.
        answer = response.text or response.clarification_question or ""
        await self.conversations.append_turn(conv, "assistant", answer)
        return IntelligenceReply(answer, ModelStatus.OK, str(profile))

    async def list_models(self) -> list[dict[str, object]]:
        return [p.public_dict() for p in self.router.profiles()]

    async def current_model(self, owner_key: str) -> str:
        conv = await self._conv(owner_key)
        return str(self._profile_for(conv))

    async def set_model(self, owner_key: str, choice: str) -> tuple[bool, str]:
        norm = choice.strip().lower()
        if norm in _VALID_PROFILES:
            conv = await self._conv(owner_key)
            await self.conversations.set_profile(conv, norm)
            return True, f"Model profile set to '{norm}'."
        # allow selecting by exact model name of a registered adapter
        for p in self.router.profiles():
            if p.available and p.model.lower() == norm:
                conv = await self._conv(owner_key)
                await self.conversations.set_profile(conv, str(p.profile))
                return True, f"Using '{p.model}' (profile '{p.profile}')."
        return False, (
            "Unknown profile/model. Valid profiles: " + ", ".join(sorted(_VALID_PROFILES))
        )

    async def reset(self, owner_key: str) -> None:
        conv = await self._conv(owner_key)
        await self.conversations.clear(conv)
