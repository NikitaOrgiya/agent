# Model Layer (Sprint 2)

## Pieces

| Piece | File | Job |
|---|---|---|
| `ModelAdapter` | `app/core/model.py` | provider-neutral interface (`profile()`, `generate()`) |
| `NullModelAdapter` | `app/core/model.py` | honest default → `MODEL_UNAVAILABLE`, never a fake answer |
| `OpenAICompatibleAdapter` | `app/adapters/openai_compatible.py` | OpenAI + any `/chat/completions` endpoint (plain httpx) |
| `AnthropicAdapter` | `app/adapters/anthropic.py` | Anthropic Messages API (plain httpx) |
| `ModelRouter` | `app/core/router.py` | pick an adapter by logical profile; one careful retry on transient errors |
| `build_router()` | `app/adapters/__init__.py` | construct the router from `Settings` |
| System contracts | `app/core/system_contract.py` | compact, versioned rules for Courier / Intelligence |
| `ContextBuilder` | `app/core/context.py` | bounded replay of recent turns (count + char budget) |

## Profiles

`economy | standard | strong | critical` (reuses `BudgetTier`). Sprint 2
registers **one** provider adapter for every profile; the point is the seam, not
running four paid models.

## Provider selection

Config only. `MODEL_PROVIDER=none` (default) → nothing available →
`MODEL_UNAVAILABLE`. A provider needs its API key **and** `MODEL_NAME` set or the
router stays unavailable (and says so in logs). Keys are env-only and never
appear in logs, errors, audit, or `/models`.

## Retry policy

`ModelRouter` retries **once** on a transient error (timeout / connection /
429 / 5xx / "overloaded"). It never retries auth (401/403), bad-request (400),
or model-not-found (404). A provider bug that raises becomes `MODEL_ERROR`, not a
crash.

## Clarification convention

The Courier contract tells the model to begin its reply with exactly
`NEEDS_CLARIFICATION: <question>` when it genuinely cannot proceed.
`classify_model_text()` turns that into `ModelResponseKind.NEEDS_CLARIFICATION`;
the Courier moves the task to `clarifying` and the next owner message continues
the same task. The Intelligence Zone does not gate on this.

## Cost controls

`MAX_MODEL_CALLS_PER_TASK` (default 2) caps model calls per task; exceeding it
fails the task. Deterministic bot commands (`/status`, `/models`, `/help`, …)
never call a model. No ensembles / debate / multi-agent calls.

## Cost data

`ModelCall.cost_usd` is set only when a provider returns it reliably. Providers
here don't, so it stays `None` — never guessed.
