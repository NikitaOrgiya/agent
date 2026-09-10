# Audit Trail

`audit_events` (PostgreSQL) is the persistent audit source. Structured logs to
stdout are kept as well, but the database is authoritative.

## What is recorded

| Event | actor | action | resource | task_id | decision | outcome |
|---|---|---|---|---|---|---|
| Task created (Courier) | `courier` / role | `task.create` | `task:<id>` | yes | – | `success` |
| Policy check | requested role | the requested action | requested `ResourceId` | if supplied | `allow` / `deny` / `require_approval` | mapped |
| Model call (Courier) | `courier` | `model.call` | `task:<id>` | yes | – | `success` / `error` |
| Model call (Intelligence) | `lab` | `model.call` | `intelligence:telegram:<id>` | – | – | `success` / `error` |
| Model unavailable | `courier` | `model.unavailable` | `task:<id>` | yes | – | `error` |

Every record carries `created_at`, a free-text `reason`, and a small `extra`
JSON blob. For model calls `extra` holds `provider`, `model`, `profile`,
`prompt_version`, `latency_ms`, `input_tokens`, `output_tokens` — **never the
prompt text or chain-of-thought**. Detailed per-call cost/latency/token metrics
also go to the dedicated `model_calls` table (basis for a future Cost Brain).

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
