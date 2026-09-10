"""Telegram message formatting helpers.

Sprint 2 sends PLAIN TEXT only (no parse_mode), which cannot be broken by
malformed Markdown in a model reply. Long replies are split on natural
boundaries under Telegram's 4096-char limit.
"""

from __future__ import annotations

_LIMIT = 3900


def chunk(text: str, limit: int = _LIMIT) -> list[str]:
    text = (text or "").strip() or "(empty response)"
    if len(text) <= limit:
        return [text]

    out: list[str] = []
    remaining = text
    while len(remaining) > limit:
        window = remaining[:limit]
        cut = window.rfind("\n\n")
        if cut < limit // 2:
            cut = window.rfind("\n")
        if cut < limit // 2:
            cut = window.rfind(" ")
        if cut <= 0:
            cut = limit
        out.append(remaining[:cut].rstrip())
        remaining = remaining[cut:].lstrip()
    if remaining:
        out.append(remaining)
    return out
