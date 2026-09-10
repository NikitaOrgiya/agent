# Policy Engine — Contract

`app/core/policy.py` is the deterministic trust boundary. No LLM output can
override it. It is **deny by default**.

## Inputs

`CapabilityRequest`: `actor` (requested role, not proven identity), `action`
(canonical dotted identifier), `resource` (canonical `ResourceId`, see
`app/core/resource.py`), `risk_level` (caller-declared), `owner_approved`.

## Evaluation order

0. **Input validation.** `action` must match
   `\A[a-z][a-z0-9]*(\.[a-z0-9][a-z0-9_]*)+\Z` and already be trimmed.
   `resource` must be a valid canonical `ResourceId` (`type:value`, no `*`, no
   `..`). Unknown actor / unknown risk level → `DENY`. Identifiers are **not**
   repaired into allowed forms.
   → `MALFORMED_ACTION` / `MALFORMED_RESOURCE` / `UNKNOWN_ACTOR` /
   `MALFORMED_RISK_LEVEL`
1. **LAB hard isolation** — above the registry, always. `LAB` requesting
   `secret.*` / `vault.*` / `wallet.*` / `payment(s).*` / `device.root` /
   `shell.*` / destructive `production.*` / any `*.delete|.destroy|.wipe|.drop
   |.purge` → `DENY` `LAB_HARD_ISOLATION`.
2. **Raw secret-material boundary** — above the registry, always.
   `secret.read_raw*` / `secret.reveal` / `secret.export` / `vault.export` /
   `vault.read_raw`: by `COURIER` → `DENY` `COURIER_NO_RAW_SECRETS`; by any role
   other than `CUSTODIAN` → `DENY` `SECRET_MATERIAL_CUSTODIAN_ONLY`.
3. **Capability Registry** (`app/core/registry.py`) is the single source of
   truth. Action absent → `DENY` `UNKNOWN_ACTION`. Action present but
   `actor ∉ spec.allowed_roles` → `DENY` `ROLE_NOT_PERMITTED`.
4. **Risk floor.** Effective risk = `max(declared, spec.min_risk,
   prefix_safety_net(action))`. A caller cannot under-declare a sensitive
   action.
5. **Approval gate.** Effective L4 → `REQUIRE_APPROVAL` unless `owner_approved`
   (`L4_OWNER_APPROVAL`). Effective L3 → `REQUIRE_APPROVAL` unless
   `owner_approved` (`L3_APPROVAL`).
6. Otherwise → `ALLOW` (`REGISTRY_ALLOW`).

Any exception during evaluation → `DENY` `EVALUATION_ERROR`. The API endpoint
wraps the engine with the same fail-closed guard **and** only returns the
decision if it was successfully written to the audit trail (see
[AUDIT.md](AUDIT.md)).

## Custodian is not a universal executor

Custodian is a trusted secret / authorization boundary. It is **not** allowed to
execute business or destructive actions (`production.delete`, `payment.execute`)
just because it holds secrets. Those actions are assigned to an executor role
(Engineer) in the registry and additionally require owner approval. A dedicated
signed capability grant for such execution is a later sprint.

## Not yet implemented

- Resource-scoped authorization (ResourceId is validated for shape, not matched
  against a per-resource ACL).
- Signed / expiring capability grants issued from an `ALLOW` decision.
- Real caller identity beyond the single Control Plane token (see
  `app/api/deps.py`); OWNER / CUSTODIAN are not requestable via the API yet.

The registry grows only through explicit, reviewed additions — never by
widening a pattern.
