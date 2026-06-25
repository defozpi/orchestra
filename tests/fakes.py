"""In-memory test doubles so the harness can be tested with no MCP/Qdrant."""

from __future__ import annotations

from typing import Any

from app.llm.base import ToolSpec


class FakeToolProvider:
    """Implements the ToolProvider protocol with canned, deterministic tools."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def list_tools(self) -> list[ToolSpec]:
        return [
            ToolSpec(
                name="search_knowledge_base",
                description="Search the KB.",
                input_schema={
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
            ),
            ToolSpec(
                name="save_note",
                description="Save a note (action).",
                input_schema={
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "content": {"type": "string"},
                    },
                    "required": ["title", "content"],
                },
            ),
        ]

    def call(self, name: str, arguments: dict[str, Any]) -> str:
        self.calls.append((name, arguments))
        if name == "search_knowledge_base":
            return (
                "[source: mcp.md] MCP reduces O(N x M) integrations to O(N + M) "
                "by standardizing the interface between models and tools."
            )
        if name == "save_note":
            return "Saved note 'x' with id 20260101T000000 -> data/notes/x.json"
        return "(unknown tool)"

    def close(self) -> None:
        pass
