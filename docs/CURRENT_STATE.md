# Current State — after Sprint 2

## Works

- **Two Telegram interfaces** (long polling, no inbound port, no webhook):
  - **Courier bot** — owner sends a task in plain language → authenticate →
    `Task` → `ModelRouter` → model → evidence + audit + model-call metadata →
    task completes → reply. `/start`, `/help`, `/status` are deterministic
    (never call a model).
  - **Intelligence Zone bot** — direct owner ↔ model conversation, *not* routed
    through the Courier planner. `/models`, `/model [<profile>]`, `/new`.
- **Owner identity** — numeric `OWNER_TELEGRAM_IDS` allowlist, deny by default;
  a bot token with an empty allowlist refuses to start. Unknown users get a bare
  "Access denied". Audit reference is `telegram:<user_id>` only.
- **Owner-approval trust boundary fixed** — `PolicyEngine.check` takes a
  server-side `PolicyContext`; a client-sent `owner_approved: true` is advisory
  only and never grants authority. L3/L4 via the public API is always
  `REQUIRE_APPROVAL`.
- **Model Router + provider adapters** — profiles `economy|standard|strong|
  critical`; `NullModelAdapter` fallback (honest `MODEL_UNAVAILABLE`);
  `OpenAICompatibleAdapter` and `AnthropicAdapter` (plain httpx, no SDK).
  Provider is turned on by config only; API keys are env-only and never logged.
- **Clarification foundation** — a model reply can be `ANSWER` or
  `NEEDS_CLARIFICATION`; the task moves to `clarifying` and the next owner
  message continues the same task (per-owner conversation binding).
- **Task lifecycle with a model** — `created → running → completed`, or
  `→ clarifying → running → completed`, or `→ failed` (clean message, no stack
  trace to Telegram). Invalid transitions rejected.
- **Evidence + model-call metadata** — a completed answer records an
  `INFERRED` `Evidence` row (`source_type=model`), and every model call records
  provider / model / profile / prompt_version / latency / tokens to the
  `model_calls` table and the audit trail. No prompt text, no chain-of-thought.
- **Cost controls** — `DEFAULT_MODEL_PROFILE`, `MAX_MODEL_CALLS_PER_TASK`
  (default 2, enforced), one model call per normal message, one careful retry on
  transient errors only.
- **Bounded context** — recent turns replayed within `CONTEXT_MAX_MESSAGES` /
  `CONTEXT_MAX_CHARS`. No long-term memory.
- **Versioned system contracts** for Courier and Intelligence; the version is
  stored in model-call metadata.
- Alembic migration `0002` (`model_calls`, `conversations`,
  `tasks.pending_question`). Everything from Sprint 1 still holds.

## Does NOT work yet

- Real device control, shell/production actions, payments.
- Secrets broker / Custodian / Agent Vault; verified (cryptographic) approval.
- Browser execution, web research (a plain answer is `INFERRED`, never
  `OBSERVED`).
- Long-term / semantic memory; multi-user conversations.
- Self-evolution, Model Arena, multi-model debate.
- Redis is still provisioned but unused by application code.

## Wired next (Sprint 3, on architect approval)

Web research / tools that upgrade evidence to `SUPPORTED`/`OBSERVED`; verified
approval via Custodian; long-term memory.

## Run

```bash
cp .env.example .env
# set: AGENTOS_CONTROL_TOKEN, POSTGRES_PASSWORD, OWNER_TELEGRAM_IDS,
#      COURIER_TELEGRAM_BOT_TOKEN and/or INTELLIGENCE_TELEGRAM_BOT_TOKEN,
#      MODEL_PROVIDER (+ MODEL_NAME + the matching API key) to connect a model
docker compose up --build
```

`kernel` serves the API on `127.0.0.1:8080` only; `telegram-gateway` runs the
bots (long polling, no port). Without `MODEL_PROVIDER` the bots still run and
answer honestly that no model is connected.

Local: `python -m app.telegram.runner` after `alembic upgrade head`.
Tests: `pytest -q` (in-memory SQLite; PostgreSQL is the only production backend).
