# Trust Model

## Non-negotiable invariants

1. Server compromise must not automatically disclose owner master secrets.
2. LAB compromise must not provide access to Vault, wallets, root or destructive production capabilities.
3. Courier cannot receive raw secret values.
4. A model output cannot override the deterministic policy engine.
5. High-risk actions require explicit approval according to risk class.
6. Privileged grants are scoped and expire.
7. Secrets must not be written to ordinary chat history, traces, prompts or logs.
8. Remote device control must be deny-by-default.
9. New tools and skills do not inherit privileges automatically.
10. Self-evolution can propose changes but cannot silently promote them to production.

## Risk levels

- L0: public read-only information and harmless local reasoning.
- L1: private read-only operations within explicitly allowed scopes.
- L2: reversible writes, drafts, branches, temporary resources.
- L3: externally visible actions or significant configuration changes.
- L4: money movement, credential/security changes, root-level actions, destructive production operations, irreversible deletion.

## Owner override

The owner may intentionally approve risky actions. Owner approval grants permission to a specific operation or bounded class of operations; it does not disable the global trust model.
