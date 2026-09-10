# Initial Architecture Decisions

## ADR-001: Hybrid sovereign architecture

The owner server is the control plane; secrets remain on trusted owner devices; expensive inference may run on external APIs or rented GPU workers.

## ADR-002: No Kubernetes in V1

The current 8 CPU / 12 GB RAM / 100 GB NVMe server is better served by Docker Compose. Kubernetes would add memory and operational overhead without solving a present problem.

## ADR-003: PostgreSQL first

PostgreSQL is the initial source of truth. Separate vector, graph and analytics databases are deferred until measurements prove they are required.

## ADR-004: No paid observability stack in V1

Start with structured audit records and ordinary logs. Langfuse or similar systems are introduced after memory headroom or a separate monitoring node exists.

## ADR-005: One paid LLM API provider initially

ChatGPT Plus and Claude Pro remain valuable human-facing subscriptions but are not treated as server API entitlements. Production automation begins with one small-budget API provider; competitors are added only if internal evaluations justify them.

## ADR-006: Intelligence Zone is direct but isolated

The owner may access LAB directly without Courier mediation. LAB freedom does not imply secret, root, wallet, or destructive production authority.
