import logging
import re
from dataclasses import dataclass

from app.core.enums import AgentRole, PolicyDecision, RiskLevel
from app.core.registry import get_action_spec
from app.core.resource import InvalidResourceId, parse_resource_id
from app.core.schemas import CapabilityRequest, PolicyResult

logger = logging.getLogger("agentos.policy")

# Canonical action identifiers are trimmed lowercase dotted paths.
# \A ... \Z (not ^ ... $) so a trailing newline cannot satisfy the anchor.
_ACTION_RE = re.compile(r"\A[a-z][a-z0-9]*(?:\.[a-z0-9][a-z0-9_]*)+\Z")

_RISK_ORDER: dict[RiskLevel, int] = {
    RiskLevel.L0: 0,
    RiskLevel.L1: 1,
    RiskLevel.L2: 2,
    RiskLevel.L3: 3,
    RiskLevel.L4: 4,
}


@dataclass(frozen=True)
class PolicyContext:
    """Trusted, server-side facts about a request.

    Only the trusted application layer constructs this. A public
    ``CapabilityRequest`` cannot set ``verified_owner_approval`` -- a client that
    sends ``owner_approved: true`` in JSON does NOT get a verified approval and
    does NOT gain authority. Real cryptographic approval arrives with Custodian;
    this is the correct trust boundary in the meantime.
    """

    verified_owner_approval: bool = False
    approval_source: str | None = None  # e.g. "custodian", "cli", "test"


_EMPTY_CONTEXT = PolicyContext()


class PolicyEngine:
    """Deterministic, deny-by-default trust-boundary rules.

    A model can recommend an action, but it can never override this layer.
    Ordering:

    0. input validation (malformed / non-canonical -> DENY)
    1. LAB hard isolation  -- above the registry, always
    2. raw secret-material boundary  -- above the registry, always
    3. Capability Registry lookup (unknown action / wrong role -> DENY)
    4. risk floor (registry min_risk, plus a prefix safety net)
    5. approval gate (effective L3 / L4 -> REQUIRE_APPROVAL unless
       PolicyContext.verified_owner_approval)
    6. ALLOW

    Any unexpected error during evaluation results in DENY (fail closed).
    """

    _secret_prefixes = ("secret.", "vault.")
    _money_prefixes = ("wallet.", "payment.", "payments.")
    _root_prefixes = (
        "device.root",
        "shell.",
        "production.delete",
        "production.destroy",
        "production.wipe",
    )
    _destructive_suffixes = (".delete", ".destroy", ".wipe", ".drop", ".purge")

    _raw_secret_actions = (
        "secret.read_raw",
        "secret.reveal",
        "secret.export",
        "vault.export",
        "vault.read_raw",
    )

    def check(
        self, req: CapabilityRequest, context: PolicyContext | None = None
    ) -> PolicyResult:
        ctx = context or _EMPTY_CONTEXT
        try:
            result = self._check(req, ctx)
        except Exception:
            logger.exception("policy evaluation error; denying request")
            return self._deny(
                "Policy evaluation failed; denying by default.", "EVALUATION_ERROR"
            )
        log = logger.warning if result.decision != PolicyDecision.ALLOW else logger.info
        log(
            "policy decision",
            extra={
                "actor": str(getattr(req, "actor", "?")),
                "action": getattr(req, "action", "?"),
                "resource": getattr(req, "resource", "?"),
                "decision": result.decision,
                "matched_rule": result.matched_rule,
                "verified_owner_approval": ctx.verified_owner_approval,
            },
        )
        return result

    def _check(self, req: CapabilityRequest, ctx: PolicyContext) -> PolicyResult:
        raw_action = req.action if isinstance(req.action, str) else ""

        # --- 0. input validation -----------------------------------------
        if (
            not raw_action
            or raw_action != raw_action.strip()
            or not _ACTION_RE.match(raw_action)
        ):
            return self._deny(
                "Malformed, empty, or non-canonical action identifier.",
                "MALFORMED_ACTION",
            )
        try:
            parse_resource_id(req.resource)
        except InvalidResourceId as exc:
            return self._deny(f"Invalid resource id: {exc}", "MALFORMED_RESOURCE")

        action = raw_action.casefold()
        if req.actor not in frozenset(AgentRole):
            return self._deny("Unknown actor role.", "UNKNOWN_ACTOR")
        if req.risk_level not in _RISK_ORDER:
            return self._deny("Unknown or malformed risk level.", "MALFORMED_RISK_LEVEL")

        # A client-supplied owner_approved flag is advisory only. Note it if it
        # disagrees with the verified context, then ignore it.
        if getattr(req, "owner_approved", False) and not ctx.verified_owner_approval:
            logger.warning(
                "ignoring client-supplied owner_approved=true (not verified) for action %r",
                action,
            )

        # --- 1. LAB hard isolation -------------------------------------
        if req.actor == AgentRole.LAB:
            forbidden = self._starts_with_any(
                action,
                self._secret_prefixes + self._money_prefixes + self._root_prefixes,
            ) or action.endswith(self._destructive_suffixes)
            if forbidden:
                return self._deny(
                    "LAB is isolated from secrets, payments, root, and destructive "
                    "production access.",
                    "LAB_HARD_ISOLATION",
                )

        # --- 2. raw secret-material boundary -----------------------
        if action in self._raw_secret_actions or action.startswith("secret.read_raw"):
            if req.actor == AgentRole.COURIER:
                return self._deny(
                    "Courier may use secret references but can never retrieve raw "
                    "secret material.",
                    "COURIER_NO_RAW_SECRETS",
                )
            if req.actor != AgentRole.CUSTODIAN:
                return self._deny(
                    "Only Custodian may access raw secret material.",
                    "SECRET_MATERIAL_CUSTODIAN_ONLY",
                )

        # --- 3. Capability Registry ---------------------------------
        spec = get_action_spec(action)
        if spec is None:
            return self._deny(
                "Action is not in the capability registry; denied by default.",
                "UNKNOWN_ACTION",
            )
        if req.actor not in spec.allowed_roles:
            return self._deny(
                f"Role '{req.actor}' is not permitted to request '{action}'.",
                "ROLE_NOT_PERMITTED",
            )

        # --- 4. risk floor -----------------------------------------
        effective_risk = self._effective_risk(action, spec.min_risk, req.risk_level)

        # --- 5. approval gate -------------------------------------
        if _RISK_ORDER[effective_risk] >= _RISK_ORDER[RiskLevel.L4] and not ctx.verified_owner_approval:
            return self._approval(
                "L4 actions always require verified owner approval.",
                "L4_OWNER_APPROVAL",
            )
        if _RISK_ORDER[effective_risk] == _RISK_ORDER[RiskLevel.L3] and not ctx.verified_owner_approval:
            return self._approval(
                "L3 actions require verified owner or delegated approval.",
                "L3_APPROVAL",
            )

        return PolicyResult(
            decision=PolicyDecision.ALLOW,
            reason="Matched a registered capability within its risk budget.",
            matched_rule="REGISTRY_ALLOW",
        )

    # --- helpers ---------------------------------------------------
    @staticmethod
    def _starts_with_any(value: str, prefixes: tuple[str, ...]) -> bool:
        return any(value.startswith(prefix) for prefix in prefixes)

    def _prefix_risk_floor(self, action: str) -> RiskLevel:
        if self._starts_with_any(
            action, self._secret_prefixes + self._money_prefixes + self._root_prefixes
        ) or action.endswith(self._destructive_suffixes):
            return RiskLevel.L4
        if action.startswith(("production.", "device.")):
            return RiskLevel.L3
        return RiskLevel.L0

    def _effective_risk(
        self, action: str, registry_min: RiskLevel, declared: RiskLevel
    ) -> RiskLevel:
        floor_value = max(
            _RISK_ORDER[registry_min], _RISK_ORDER[self._prefix_risk_floor(action)]
        )
        return declared if _RISK_ORDER[declared] >= floor_value else _by_value(floor_value)

    @staticmethod
    def _deny(reason: str, rule: str) -> PolicyResult:
        return PolicyResult(decision=PolicyDecision.DENY, reason=reason, matched_rule=rule)

    @staticmethod
    def _approval(reason: str, rule: str) -> PolicyResult:
        return PolicyResult(
            decision=PolicyDecision.REQUIRE_APPROVAL,
            reason=reason,
            matched_rule=rule,
        )


_RISK_BY_VALUE: dict[int, RiskLevel] = {v: k for k, v in _RISK_ORDER.items()}


def _by_value(value: int) -> RiskLevel:
    return _RISK_BY_VALUE[value]
