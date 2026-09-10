# Current State — after Sprint 1

## What Agent OS can do now

- **Run locally** as a FastAPI control plane (Python venv or Docker Compose).
- **Managed schema.** PostgreSQL schema is created and versioned by Alembic
  (`alembic upgrade head`). The application process never alters the schema.
- **Authenticated control plane.** `/v1/*` requires a bearer Control Plane token
  (`AGENTOS_CONTROL_TOKEN`, env only). `/health` and `/readiness` are open.
- **Identity vs. requested role.** The token authenticates one caller
  (`control-plane`). The `actor` / `requested_actor` field in a request is only
  a *request* to act as a role; the caller cannot become `owner` or `custodian`
  through JSON — those roles are not requestable via the Sprint 1 token.
- **Deterministic policy engine**, deny-by-default, backed by a central
  **Capability Registry** (`app/core/registry.py`) — one source of truth for
  action → allowed roles / minimum risk. See [POLICY.md](POLICY.md).
- **Canonical ResourceId** contract (`type:value`, e.g. `project:agent-os`,
  `secretref:openai/main`). No `*` full-access. OS paths are never capability
  resources. See `app/core/resource.py`.
- **Persistent audit trail** in `audit_events` for task creation and every
  policy decision, with a documented fail-closed policy. See [AUDIT.md](AUDIT.md).
- **Task lifecycle** with enforced state transitions
  (`created → … → completed/failed/cancelled`); invalid transitions are rejected.
- **Courier foundation** (no Telegram, no LLM): accepts an authenticated
  request, creates a task, records it, and honestly reports that execution
  intelligence is not connected.
- **Provider-neutral Model Adapter interface** with a `NullModelAdapter` that
  returns `MODEL_UNAVAILABLE` instead of fabricating an answer.
- **/health** (liveness) and **/readiness** (checks the database; no secrets,
  DSNs, or stack traces in responses).

## What it deliberately does NOT do yet

- No Telegram Courier, no LLM/model provider (OpenAI / Anthropic / local).
- No Custodian, Agent Vault, secret broker, device or browser control.
- No real multi-identity auth, no signed / expiring capability grants issued
  from an `ALLOW`, no resource-scoped ACLs.
- No task *execution* — a submitted task is recorded and then waits; nothing
  processes it.
- Redis is provisioned by Compose but not yet used by application code.
- No audit read API, no tamper-evidence on the audit log.

## Wired next (Sprint 2, on architect approval)

- Telegram Courier interface + owner identity verification.
- One low-cost LLM provider behind the existing `ModelAdapter` interface,
  selected by a minimal Model Router; Courier core unchanged.
- Task processing path: Courier → ModelAdapter → task transitions + evidence.

## Run it

Local (venv):

```
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"      # Windows
# .venv/bin/python -m pip install -e ".[dev]"        # Linux/macOS
copy .env.example .env    # then set AGENTOS_CONTROL_TOKEN
.venv\Scripts\python -m alembic upgrade head          # needs PostgreSQL
.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8080
```

Docker:

```
cp .env.example .env      # set AGENTOS_CONTROL_TOKEN and POSTGRES_PASSWORD
docker compose up --build # API on http://127.0.0.1:8080 only
```

Tests: `.venv\Scripts\python -m pytest -q` (uses in-memory SQLite; PostgreSQL is
the only production backend).
