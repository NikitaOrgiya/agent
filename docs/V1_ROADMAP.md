# V1 Roadmap

## Milestone A — Foundation (current repository)

Control-plane API, PostgreSQL, Redis, task schema, capability schema, deterministic Guardian rules, audit/evidence primitives.

Exit condition: the service runs reproducibly and hard trust-boundary tests pass.

## Milestone B — Courier

Private Telegram bot, owner identity verification, task intake, clarification state, provider-neutral model adapter, one low-cost LLM API provider.

Exit condition: owner can create a task in Telegram and receive a non-privileged model-assisted response with complete trace metadata.

## Milestone C — Truth and Memory

Evidence capture, source freshness, world-state records, project memory, retrieval, answer truth labels.

Exit condition: important factual answers can distinguish observed/supported/inferred/uncertain/unknown information.

## Milestone D — Guardian and capabilities

Capability issuance, expirations, approval flows, risk classification, kill switch, immutable-ish audit export.

Exit condition: privileged tools cannot execute without a valid policy decision and scoped grant.

## Milestone E — Trusted Device and Custodian

Local Device Node, local Guardian Sentinel, OS keychain / credential broker, authenticated browser bridge, signed capability verification.

Exit condition: server can request a bounded action on the trusted device without learning the credential used to authorize it.

## Milestone F — Intelligence Zone

Direct owner interface, local/open-weight model endpoints, optional rented GPU workers, isolated tool set.

Exit condition: owner can talk directly to LAB while LAB remains technically unable to cross into the Vault trust domain.

## Milestone G — Specialist execution

Browser executor, coding agent workspaces, research workers, news ingestion, Telegram news group, GitHub watchtower.

## Milestone H — Evaluation and evolution

Model Arena, private benchmarks, cost/latency/quality scoring, champion/challenger routing, gated skill improvement and red-team regression suite.
