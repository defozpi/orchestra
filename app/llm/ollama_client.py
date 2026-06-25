"""Ollama client — fully-local, offline tool-calling provider.

Lets the whole agent run with no cloud API at all (use a tool-capable model such
as llama3.1). Talks to the Ollama HTTP API and maps its tool-call format to the
harness's neutral types.
"""

from __future__ import annotations

from typing import Any

import httpx

from app.config import get_settings
from app.llm.base import AssistantTurn, ToolCall, ToolSpec


class OllamaClient:
    name = "ollama"

    def __init__(self) -> None:
        settings = get_settings()
        self._url = settings.ollama_base_url.rstrip("/")
        self._model = settings.ollama_model
        self._temperature = settings.temperature

    def complete(
        self,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[ToolSpec],
    ) -> AssistantTurn:
        payload = {
            "model": self._model,
            "stream": False,
            "options": {"temperature": self._temperature},
            "messages": [{"role": "system", "content": system}]
            + self._to_ollama(messages),
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.input_schema,
                    },
                }
                for t in tools
            ],
        }
        with httpx.Client(timeout=120) as client:
            resp = client.post(f"{self._url}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()

        msg = data.get("message", {})
        tool_calls = []
        for i, raw in enumerate(msg.get("tool_calls", []) or []):
            fn = raw.get("function", {})
            args = fn.get("arguments", {})
            if isinstance(args, str):
                import json

                try:
                    args = json.loads(args)
                except Exception:
                    args = {}
            tool_calls.append(
                ToolCall(id=f"ollama_call_{i}", name=fn.get("name", ""), arguments=args)
            )
        return AssistantTurn(text=(msg.get("content") or "").strip(), tool_calls=tool_calls)

    @staticmethod
    def _to_ollama(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for m in messages:
            if m["role"] == "user":
                out.append({"role": "user", "content": m["content"]})
            elif m["role"] == "assistant":
                entry: dict[str, Any] = {"role": "assistant", "content": m.get("text", "")}
                if m.get("tool_calls"):
                    entry["tool_calls"] = [
                        {"function": {"name": tc.name, "arguments": tc.arguments}}
                        for tc in m["tool_calls"]
                    ]
                out.append(entry)
            elif m["role"] == "tool":
                out.append(
                    {"role": "tool", "name": m["name"], "content": m["content"]}
                )
        return out
