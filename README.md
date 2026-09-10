# Agent OS — V0 Foundation

This repository is the first implementation layer of a personal, security-first Agent OS.

The V0 goal is deliberately narrow: establish a trustworthy control plane before giving any model real-world authority.

## Core principles

1. **No fabrication by design** — unknown facts must remain unknown until supported by evidence.
2. **Least privilege** — agents receive scoped, short-lived capabilities, never broad ambient authority.
3. **Secrets are references, not prompt content** — models may see `secret://...`, never raw credentials.
4. **Intelligence is not authority** — the most capable model is not automatically the most privileged actor.
5. **Clarify material ambiguity** — uncertainty that changes the result must be resolved before costly or risky work.
6. **Minimum necessary work** — the orchestrator should choose the smallest sufficient workflow.
7. **Learning is gated** — traces may produce improvement proposals, but production changes require evaluation and approval.
8. **Audit everything important** — privileged decisions and actions must be attributable and reviewable.

## What exists now (after Sprint 1)

- FastAPI control-plane service, loopback-only by default
- PostgreSQL schema managed by **Alembic migrations** (not by app startup)
- deterministic **deny-by-default** policy engine backed by a central
  **Capability Registry**
- canonical **ResourceId** contract (logical ids, never OS paths)
- **Control Plane token auth** on `/v1/*`; requested role is separate from the
  authenticated caller
- **persistent audit trail** (`audit_events`) with a fail-closed policy
- task lifecycle with enforced state transitions
- **Courier** domain foundation (no Telegram, no LLM) + provider-neutral
  **ModelAdapter** interface with an honest `MODEL_UNAVAILABLE` null adapter
- `/health` (liveness) and `/readiness` (database check)
- architecture, trust model, threat model, policy, audit and current-state docs

See [docs/CURRENT_STATE.md](docs/CURRENT_STATE.md) for the full picture.

## Deliberately not present yet

Telegram execution · LLM provider integration · device / browser control ·
secrets broker / Custodian · autonomous execution · self-evolution ·
resource-scoped ACLs · signed capability grants.

## Quick start (Docker)

```bash
cp .env.example .env      # set AGENTOS_CONTROL_TOKEN and POSTGRES_PASSWORD
docker compose up --build
```

API is exposed on `http://127.0.0.1:8080` only.

## Quick start (local venv)

```bash
python -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"     # Windows: .venv\Scripts\python
cp .env.example .env                             # set AGENTOS_CONTROL_TOKEN
.venv/bin/python -m alembic upgrade head          # requires PostgreSQL
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8080
```

Endpoints: `GET /health`, `GET /readiness`, `POST /v1/tasks`,
`GET /v1/tasks/{id}`, `POST /v1/policy/check` (the `/v1/*` routes need
`Authorization: Bearer <AGENTOS_CONTROL_TOKEN>`). Interactive docs at `/docs`.

Tests: `pytest -q` (in-memory SQLite; PostgreSQL remains the only production DB).

## Next milestone

Telegram Courier interface + one low-cost model provider behind the existing
adapter interface. Still no raw secret access and no destructive device authority.
