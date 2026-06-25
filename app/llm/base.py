"""The LLM contract the harness depends on.

The harness never imports a concrete provider — it depends only on these neutral
types and the `LLMClient` protocol. That is what lets Claude, a local Ollama
model, or the deterministic mock be swapped via one env var (Skills rule #5:
"the agent runtime is interchangeable").

Neutral conversation format (a list of these dicts):
    {"role": "user",      "content": "..."}
    {"role": "assistant", "text": "...", "tool_calls": [ToolCall, ...]}
    {"role": "tool",      "tool_call_id": "...", "name": "...", "content": "..."}
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class ToolSpec:
    """A tool advertised to the model (mirrors an MCP tool definition)."""

    name: str
    description: str
    input_schema: dict[str, Any]


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class AssistantTurn:
    """One model turn: optional prose plus any tool calls it requested."""

    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)

    @property
    def wants_tools(self) -> bool:
        return bool(self.tool_calls)


class LLMClient(Protocol):
    name: str

    def complete(
        self,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[ToolSpec],
    ) -> AssistantTurn:
        """Produce the next assistant turn given the conversation and tools."""
        ...
