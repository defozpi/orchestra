"""Context-budget management.

"Active context is a budget, not a vessel" (RAG / context-rot chapter). Tool
outputs are the noisiest, fastest-growing part of an agent's context, so when the
running estimate exceeds the budget we trim the *oldest tool results* first while
always preserving the original user request and the most recent turns.

The token estimate is a deliberately cheap heuristic (~4 chars/token); the goal
is a guardrail against unbounded growth, not exact accounting.
"""

from __future__ import annotations

from typing import Any


def estimate_tokens(messages: list[dict[str, Any]]) -> int:
    chars = 0
    for m in messages:
        chars += len(m.get("content", "") or "")
        chars += len(m.get("text", "") or "")
        for tc in m.get("tool_calls", []):
            chars += len(str(tc.arguments))
    return chars // 4


def trim_to_budget(messages: list[dict[str, Any]], max_tokens: int) -> list[dict[str, Any]]:
    """Drop oldest tool results until under budget, keeping the first user
    message and the last two turns intact."""
    if estimate_tokens(messages) <= max_tokens or len(messages) <= 3:
        return messages

    protected_tail = 2
    out = list(messages)
    # indices eligible for trimming: tool messages not in the protected tail,
    # and not the very first user message.
    for i in range(1, len(out) - protected_tail):
        if estimate_tokens(out) <= max_tokens:
            break
        if out[i] is not None and out[i].get("role") == "tool":
            content = out[i]["content"]
            if len(content) > 200:
                out[i] = {**out[i], "content": content[:200] + " …[trimmed]"}
    return out
