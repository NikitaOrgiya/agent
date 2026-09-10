# Threat Model — Initial

## Assets

The highest-value assets are owner credentials, authenticated browser sessions, private keys, device control, personal files, project source code, private knowledge, and the integrity of the Agent OS itself.

## Primary threat classes

### Prompt injection

Untrusted websites, documents, messages or repositories may contain instructions intended to redirect an agent. Mitigation: content is data, not authority; tools are capability-gated; secrets are brokered outside model context.

### Agent hallucination

A model may invent a fact, action result or permission. Mitigation: evidence objects, tool result verification, explicit truth states, audit trails and deterministic policy checks.

### Server compromise

The control plane is internet-adjacent and therefore assumed compromisable. Mitigation: no master secrets on the server; trusted Device Nodes independently validate capabilities; private device networking; least privilege.

### Malicious / compromised tool

An MCP or external tool may leak data or exceed its declared behavior. Mitigation: tool allowlists, sandboxing, per-tool permissions, provenance, network restrictions and later tool signing/review.

### Supply-chain compromise

Third-party repositories and dependencies may become malicious. Mitigation: pinned dependencies, release review, SBOM/vulnerability scanning, canary upgrades, rollback.

### Self-evolution regression

Automated prompt/skill changes may degrade safety or quality. Mitigation: offline candidates, regression suites, red-team tests, benchmark gates and explicit promotion.

## Security assumption

No LLM is treated as a security boundary. Security boundaries are implemented in deterministic code and operating-system / network controls.
