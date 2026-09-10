"""Bounded conversation context builder.

No semantic memory. Just a hard cap on how much recent history is replayed to
the model, by message count and approximate character budget. Long-term memory
is a later sprint.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Turn:
    role: str  # "user" | "assistant"
    content: str


@dataclass(frozen=True)
class ContextBuilder:
    max_messages: int = 12
    max_chars: int = 12_000

    def build(self, turns: list[Turn] | tuple[Turn, ...]) -> tuple[dict[str, str], ...]:
        """Return the trimmed history (oldest first) as provider-neutral dicts.

        Keeps the most recent turns within both limits. The caller adds the
        system prompt and the current user message separately.
        """
        recent = list(turns)[-self.max_messages:]
        budget = self.max_chars
        kept: list[Turn] = []
        for turn in reversed(recent):
            cost = len(turn.content) + 16
            if kept and cost > budget:
                break
            budget -= cost
            kept.append(turn)
        kept.reverse()
        return tuple({"role": t.role, "content": t.content} for t in kept)
