import logging
import re

from app.core.enums import AgentRole, PolicyDecision, RiskLevel
from app.core.schemas import CapabilityRequest, PolicyResult

logger = logging.getLogger("agentos.policy")

# Canonical identifiers are lowercase dotted paths, e.g. "secret.read_raw",
# "web.read_public". Anything else is treated as malformed and denied.
# \A ... \Z (not ^ ... $) so a trailing newline cannot satisfy the anchor.
_ACTION_RE = re.compile(r"\A[a-z][a-z0-9]*(?:\.[a-z0-9][a-z0-9_]*)+\Z")
_RESOURCE_RE = re.compile(r"\A[a-z0-9][a-z0-9_.:/@-]{0,499}\Z")

_RISK_ORDER: dict[RiskLevel, int] = {
    RiskLevel.L0: 0,
    RiskLevel.L1: 1,
    RiskLevel.L2: 2,
    RiskLevel.L3: 3,
    RiskLevel.L4: 4,
}


class PolicyEngine:
    """Deterministic, deny-by-default trust-boundary rules.

    A model can recommend an action, but it can never override this layer.
    Every path that is not an explicit, well-formed, allow-listed request within
    its risk budget results in DENY or REQUIRE_APPROVAL. Any unexpected error
    during evaluation also results in DENY (fail closed).
    """

    # --- hard isolation prefixes ---------------------------------------------
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

    # Actions that would expose raw secret material. Never available to a model
    # role; Custodian only, and even then brokering is preferred.
    _raw_secret_actions = (
        "secret.read_raw",
        "secret.reveal",
        "secret.export",
        "vault.export",
        "vault.read_raw",
    )

    # --- explicit allowlist -------------------------------------------------
    # (action or "prefix.") -> roles permitted to request it. Anything not
    # covered here is denied by default. Risk / approval gates still apply on
    # top of a match. This is the V0 seed vocabulary; it is expected to grow
    # through explicit, reviewed additions only.
    _allow_rules: tuple[tuple[str, frozenset[AgentRole]], ...] = (
        ("policy.check", frozenset(AgentRole)),
        ("health.read", frozenset(AgentRole)),
        (
            "task.read",
            frozenset(
                {AgentRole.OWNER, AgentRole.COURIER, AgentRole.GUARDIAN, AgentRole.LAB}
            ),
        ),
        ("task.create", frozenset({AgentRole.OWNER, AgentRole.COURIER})),
        (
            "reasoning.local",
            frozenset(
                {
                    AgentRole.LAB,
                    AgentRole.RESEARCHER,
                    AgentRole.ENGINEER,
                    AgentRole.VERIFIER,
                    AgentRole.COURIER,
                    AgentRole.GUARDIAN,
                }
            ),
        ),
        (
            "web.read_public",
            frozenset(
                {
                    AgentRole.LAB,
                    AgentRole.RESEARCHER,
                    AgentRole.BROWSER,
                    AgentRole.COURIER,
                }
            ),
        ),
        (
            "evidence.read",
            frozenset(
                {
                    AgentRole.OWNER,
                    AgentRole.COURIER,
                    AgentRole.GUARDIAN,
                    AgentRole.VERIFIER,
                    AgentRole.LAB,
                }
            ),
        ),
        (
            "evidence.write",
            frozenset(
                {
                    AgentRole.COURIER,
                    AgentRole.RESEARCHER,
                    AgentRole.VERIFIER,
                    AgentRole.GUARDIAN,
                }
            ),
        ),
        # Reference-based secret use (SecretRef identifiers, never raw material).
        (
            "secret.use_ref",
            frozenset(
                {
                    AgentRole.COURIER,
                    AgentRole.CUSTODIAN,
                    AgentRole.ENGINEER,
                    AgentRole.BROWSER,
                }
            ),
        ),
        # Raw secret material / vault operations: Custodian only.
        ("secret.read_raw", frozenset({AgentRole.CUSTODIAN})),
        ("vault.", frozenset({AgentRole.CUSTODIAN})),
        # Money movement: Custodian or Owner, always with approval (risk floor L4).
        ("wallet.", frozenset({AgentRole.CUSTODIAN, AgentRole.OWNER})),
        ("payment.", frozenset({AgentRole.CUSTODIAN, AgentRole.OWNER})),
        ("payments.", frozenset({AgentRole.CUSTODIAN, AgentRole.OWNER})),
        # Destructive production / device actions: explicit owner approval only.
        (
            "production.delete",
            frozenset({AgentRole.CUSTODIAN, AgentRole.OWNER, AgentRole.ENGINEER}),
        ),
        ("device.", frozenset({AgentRole.CUSTODIAN, AgentRole.OWNER})),
    )

    def check(self, req: CapabilityRequest) -> PolicyResult:
        try:
            result = self._check(req)
        except Exception:  # noqa: BLE001 - fail closed on any evaluation error
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
            },
        )
        return result

    def _check(self, req: CapabilityRequest) -> PolicyResult:
        raw_action = req.action if isinstance(req.action, str) else ""
        raw_resource = req.resource if isinstance(req.resource, str) else ""

        # --- 0. Input validation: malformed / non-canonical request => DENY --
        # Canonical identifiers are already-trimmed lowercase dotted paths. We do
        # not "repair" a non-canonical identifier into an allowed one; we deny it.
        if (
            not raw_action
            or raw_action != raw_action.strip()
            or not _ACTION_RE.match(raw_action)
        ):
            return self._deny(
                "Malformed, empty, or non-canonical action identifier.",
                "MALFORMED_ACTION",
            )
        if (
            not raw_resource
            or raw_resource != raw_resource.strip()
            or raw_resource == "*"
            or ".." in raw_resource
            or not _RESOURCE_RE.match(raw_resource)
        ):
            return self._deny(
                "Malformed, empty, wildcard, or unspecified resource identifier.",
                "MALFORMED_RESOURCE",
            )

        # Defense in depth: fold case before every boundary comparison so a
        # would-be "SECRET.read_raw" can never miss an isolation prefix even if
        # the canonical-form check above is ever loosened.
        action = raw_action.casefold()
        if req.actor not in frozenset(AgentRole):
            return self._deny("Unknown actor role.", "UNKNOWN_ACTOR")

        # --- 1. Hard isolation: enforced before any allow logic --------------
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

        # --- 2. Explicit allowlist: absence of a rule => DENY ---------------
        allowed_roles = self._match_allow_rule(action)
        if allowed_roles is None:
            return self._deny(
                "No allow rule matches this action; denied by default.",
                "NO_MATCHING_ALLOW_RULE",
            )
        if req.actor not in allowed_roles:
            return self._deny(
                f"Role '{req.actor}' is not permitted to request this action.",
                "ROLE_NOT_PERMITTED",
            )

        # --- 3. Risk floor: caller cannot under-declare a sensitive action --
        if req.risk_level not in _RISK_ORDER:
            return self._deny("Unknown or malformed risk level.", "MALFORMED_RISK_LEVEL")
        effective_risk = self._effective_risk(action, req.risk_level)

        if _RISK_ORDER[effective_risk] >= _RISK_ORDER[RiskLevel.L4] and not req.owner_approved:
            return self._approval(
                "L4 actions always require explicit owner approval.",
                "L4_OWNER_APPROVAL",
            )
        if _RISK_ORDER[effective_risk] == _RISK_ORDER[RiskLevel.L3] and not req.owner_approved:
            return self._approval(
                "L3 actions require explicit owner or delegated approval.",
                "L3_APPROVAL",
            )

        return PolicyResult(
            decision=PolicyDecision.ALLOW,
            reason="Matched an explicit allow rule within its risk budget.",
            matched_rule="EXPLICIT_ALLOW",
        )

    # --- helpers -----------------------------------------------------------
    @staticmethod
    def _starts_with_any(value: str, prefixes: tuple[str, ...]) -> bool:
        return any(value.startswith(prefix) for prefix in prefixes)

    def _match_allow_rule(self, action: str) -> frozenset[AgentRole] | None:
        matched: frozenset[AgentRole] | None = None
        for key, roles in self._allow_rules:
            if action == key or (key.endswith(".") and action.startswith(key)):
                matched = roles if matched is None else (matched | roles)
        return matched

    def _effective_risk(self, action: str, declared: RiskLevel) -> RiskLevel:
        floor = RiskLevel.L1
        if self._starts_with_any(
            action, self._secret_prefixes + self._money_prefixes + self._root_prefixes
        ) or action.endswith(self._destructive_suffixes):
            floor = RiskLevel.L4
        elif action.startswith(("production.", "device.")):
            floor = RiskLevel.L3
        if _RISK_ORDER[declared] >= _RISK_ORDER[floor]:
            return declared
        return floor

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
