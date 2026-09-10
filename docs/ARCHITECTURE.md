# Agent OS Architecture

## Trust domains

```text
                           OWNER
              ┌──────────────┼──────────────┐
              │              │              │
          COURIER UI     DIRECT LAB UI   TRUSTED UI
              │              │              │
              └───────┬──────┘              │
                      ▼                     │
              ┌──────────────────┐          │
              │   CONTROL PLANE  │          │
              │   owner server   │          │
              │                  │          │
              │ Kernel           │          │
              │ Task Manager     │          │
              │ Router/Planner   │          │
              │ Guardian Core    │          │
              │ Truth Engine     │          │
              │ Memory/Knowledge │          │
              │ Tool Registry    │          │
              │ Audit            │          │
              └────────┬─────────┘          │
                       │                    │
          ┌────────────┼────────────┐       │
          ▼            ▼            ▼       ▼
      CLOUD AI      SANDBOX      KNOWLEDGE  TRUSTED DEVICE
                                   SOURCES      │
                                               │
                                      ┌────────┴────────┐
                                      │ Custodian       │
                                      │ Guardian Node   │
                                      │ Device Executor │
                                      │ Secret Broker   │
                                      └────────┬────────┘
                                               │
                                               ▼
                                          SECRET ZONE
```

## Role boundaries

### Courier

Owner-facing orchestrator. It may request capabilities but cannot retrieve raw secrets.

### Custodian

Local trusted authority on owner devices. It brokers credentials and may issue scoped, short-lived capabilities. Even Custodian should prefer non-disclosure credential injection over presenting secrets to an LLM.

### Intelligence Zone / LAB

Direct owner-accessible reasoning environment. It may be highly permissive in what it can analyze, but it is isolated from secrets, wallets, root authority, and destructive production operations.

### Guardian

Two layers: deterministic policy enforcement and an optional security reasoning model. Hard trust boundaries live in code, not prompts.

## Capability model

Agents never receive permanent global authority. A privileged operation must be represented as a grant such as:

- actor
- task
- action
- resource
- scope
- issuer
- expiry
- call budget
- revocation state

Cryptographic signing is introduced before remote Device Nodes are enabled.

## Data planes

**PostgreSQL** stores source-of-truth state, task history, audit metadata, evidence metadata, world state and later vector embeddings.

**Redis** stores short-lived queues, locks and caches only. It is never the sole source of important state.

**Object storage** is introduced later for large artifacts, screenshots, datasets and archives.

## Model strategy

No agent is permanently tied to one vendor. The future Model Router selects a model by capability, cost and benchmark score. The first production integration should use one paid API provider only; additional providers are added only when measured value justifies the cost.
