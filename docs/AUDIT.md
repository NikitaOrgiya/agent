# Audit Trail

`audit_events` (PostgreSQL) is the persistent audit source. Structured logs to
stdout are kept as well, but the database is authoritative.

## What is recorded

| Event | actor | action | resource | task_id | decision | outcome |
|---|---|---|---|---|---|---|
| Task created (via Courier) | requested role | `task.create` | `task:<id>` | yes | – | `success` |
| Policy check | requested role | the requested action | requested `ResourceId` | if supplied | `allow` / `deny` / `require_approval` | mapped outcome |

Every record carries `created_at`, a free-text `reason`, and a small `extra`
JSON blob (`matched_rule`, `caller`, …).

## Never stored

Raw secret values. Callers must not put secrets in `reason` / `extra`.
`AuditService._redact` defensively masks keys that look sensitive
(`secret`, `token`, `password`, `authorization`, `api_key`), but the contract is
that callers do not pass secrets in the first place.

## Fail-safe policy

The audit write shares the caller's database transaction (`flush`, not
`commit`; the API layer owns the `commit`).

**If the audit write or its commit fails during a security-sensitive
operation, the operation is not reported as successful.**

Concretely for `POST /v1/policy/check`: if the decision cannot be persisted, the
endpoint rolls back and returns **503**, logging `CRITICAL`. The caller never
receives a policy decision (which could be `ALLOW`) that was not recorded. This
is deliberately conservative: audit is on the critical path for that endpoint.

A missing audit record therefore never silently becomes a completed action.

## Not yet implemented

- Tamper-evidence / hash chaining / append-only export.
- Retention and rotation.
- A read API for the audit trail.
