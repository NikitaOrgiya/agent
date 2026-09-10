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

## What exists now (after Sprint 2)

- FastAPI control-plane service (`kernel`), loopback-only, Alembic-managed schema
- deterministic **deny-by-default** policy engine + central **Capability
  Registry**; owner approval is a **server-side `PolicyContext`**, never a
  client JSON flag
- canonical **ResourceId** contract (logical ids, never OS paths)
- **Control Plane token auth** on `/v1/*`; **persistent audit trail** with a
  fail-closed policy
- **Telegram gateway** (`telegram-gateway`, long polling, no inbound port):
  - **Courier bot** — task in → model → evidence/audit → answer
  - **Intelligence Zone bot** — direct owner ↔ model chat, separate token
- numeric **owner allowlist**, deny by default
- **Model Router** + `OpenAI` / `OpenAI-compatible` / `Anthropic` adapters
  (plain httpx, no SDK), honest `MODEL_UNAVAILABLE` fallback
- **clarification** foundation, bounded **conversation context**, versioned
  **system contracts**, **cost controls** (`MAX_MODEL_CALLS_PER_TASK`)
- `model_calls` metadata table (provider/model/profile/latency/tokens) for a
  future Cost Brain

See [docs/CURRENT_STATE.md](docs/CURRENT_STATE.md) and
[docs/MODEL_LAYER.md](docs/MODEL_LAYER.md).

## Deliberately not present yet

Device / browser / shell / payment execution · secrets broker / Custodian ·
verified cryptographic approval · web research · long-term memory ·
self-evolution · Model Arena.

## Quick start (Docker)

```bash
cp .env.example .env
# set AGENTOS_CONTROL_TOKEN, POSTGRES_PASSWORD, OWNER_TELEGRAM_IDS,
# a bot token, and (optionally) MODEL_PROVIDER + MODEL_NAME + an API key
docker compose up --build
```

`kernel` API on `127.0.0.1:8080` only; `telegram-gateway` polls Telegram.

## Quick start (local venv)

```bash
python -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"     # Windows: .venv\Scripts\python
cp .env.example .env
.venv/bin/python -m alembic upgrade head          # requires PostgreSQL
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8080   # API
.venv/bin/python -m app.telegram.runner                                 # bots
```

`/v1/*` needs `Authorization: Bearer <AGENTOS_CONTROL_TOKEN>`. Interactive docs
at `/docs`. Tests: `pytest -q` (in-memory SQLite; PostgreSQL is the only
production backend).

## Next milestone

Web research / tools (evidence upgraded to `SUPPORTED`/`OBSERVED`), verified
approval via Custodian, long-term memory. Still no raw secret access and no
destructive device authority.
