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

## V0 provides

- FastAPI control-plane service
- PostgreSQL-backed task, capability, evidence and audit models
- deterministic policy engine
- risk / approval model
- Docker Compose foundation with PostgreSQL and Redis
- architecture, trust model, threat model, and V1 roadmap
- tests for critical trust-boundary rules

## V0 deliberately does not provide yet

- Telegram execution
- LLM provider integration
- device control
- secrets broker / Custodian
- browser automation
- autonomous code execution
- self-evolution

Those layers are added only after the trust model exists and is tested.

## Quick start

Copy `.env.example` to `.env`, then run:

```bash
docker compose up --build
```

Health endpoint:

```text
GET http://localhost:8080/health
```

API docs:

```text
http://localhost:8080/docs
```

## Next milestone

V0.1 adds the Telegram Courier interface and a provider-neutral model adapter. It should still have no raw secret access and no destructive device authority.
