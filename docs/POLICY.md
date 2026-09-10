# Policy Engine — V0 Contract

`app/core/policy.py` is the deterministic trust boundary. No LLM output can
override it. It is **deny by default**.

## Evaluation order

1. **Input validation.** `action` must be a canonical lowercase dotted identifier
   (`^[a-z][a-z0-9]*(\.[a-z0-9][a-z0-9_]*)+$`, already trimmed). `resource` must
   be a concrete, non-wildcard, non-`..` identifier. Anything else → `DENY`
   (`MALFORMED_ACTION` / `MALFORMED_RESOURCE`). Non-string or unknown actor →
   `DENY`. Identifiers are **not** repaired into allowed forms.
2. **Hard isolation** (cannot be granted by any allow rule or owner approval):
   - `LAB` requesting `secret.*`, `vault.*`, `wallet.*`, `payment(s).*`,
     `device.root`, `shell.*`, destructive `production.*`, or any `*.delete /
     .destroy / .wipe / .drop / .purge` → `DENY` (`LAB_HARD_ISOLATION`).
   - `secret.read_raw*` / `secret.reveal` / `secret.export` / `vault.export` /
     `vault.read_raw` by `COURIER` → `DENY` (`COURIER_NO_RAW_SECRETS`); by any
     role other than `CUSTODIAN` → `DENY` (`SECRET_MATERIAL_CUSTODIAN_ONLY`).
3. **Explicit allowlist.** `_allow_rules` maps an action (or `prefix.`) to the
   set of roles permitted to request it. No match → `DENY`
   (`NO_MATCHING_ALLOW_RULE`). Match but wrong role → `DENY`
   (`ROLE_NOT_PERMITTED`).
4. **Risk floor.** The engine raises the caller-declared `risk_level` to a
   minimum derived from the action (secrets / money / root / destructive → L4;
   other `production.*` / `device.*` → L3). A caller cannot under-declare risk.
5. **Approval gate.** Effective L4 → `REQUIRE_APPROVAL` unless `owner_approved`.
   Effective L3 → `REQUIRE_APPROVAL` unless `owner_approved`.
6. Otherwise → `ALLOW` (`EXPLICIT_ALLOW`).

Any exception during evaluation → `DENY` (`EVALUATION_ERROR`). The API endpoint
wraps the engine with the same fail-closed guard.

## Not yet implemented (V1+)

- Persisted audit records for every decision (currently structured logs only).
- Resource-scoped allow rules (resources are validated for shape, not matched).
- Signed / expiring capability grants issued from an `ALLOW` decision.
- Caller authentication / authorization for the `/v1/policy/check` endpoint.

The allowlist in `_allow_rules` is a seed vocabulary. It grows only through
explicit, reviewed additions — never by widening a pattern.
