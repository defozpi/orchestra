"""Anthropic Claude client — the default provider.

Translates the harness's neutral conversation format into the Anthropic Messages
API (tool_use / tool_result blocks) and back. Claude is the most capable option
and gives the strongest "agent + harness" story; it is used whenever
ANTHROPIC_API_KEY is set.
"""

from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.llm.base import AssistantTurn, ToolCall, ToolSpec


class AnthropicClient:
    name = "anthropic"

    def __init__(self) -> None:
        import anthropic

        settings = get_settings()
        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self._model = settings.anthropic_model
        self._temperature = settings.temperature

    def complete(
        self,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[ToolSpec],
    ) -> AssistantTurn:
        resp = self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            temperature=self._temperature,
            system=system,
            tools=[
                {
                    "name": t.name,
                    "description": t.description,
                    "input_schema": t.input_schema,
                }
                for t in tools
            ],
            messages=self._to_anthropic(messages),
        )

        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []
        for block in resp.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(
                    ToolCall(id=block.id, name=block.name, arguments=dict(block.input))
                )
        return AssistantTurn(text="".join(text_parts).strip(), tool_calls=tool_calls)

    # -- neutral -> Anthropic format ------------------------------------
    @staticmethod
    def _to_anthropic(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for m in messages:
            role = m["role"]
            if role == "user":
                out.append({"role": "user", "content": m["content"]})
            elif role == "assistant":
                content: list[dict[str, Any]] = []
                if m.get("text"):
                    content.append({"type": "text", "text": m["text"]})
                for tc in m.get("tool_calls", []):
                    content.append(
                        {
                            "type": "tool_use",
                            "id": tc.id,
                            "name": tc.name,
                            "input": tc.arguments,
                        }
                    )
                out.append({"role": "assistant", "content": content})
            elif role == "tool":
                block = {
                    "type": "tool_result",
                    "tool_use_id": m["tool_call_id"],
                    "content": m["content"],
                }
                # Anthropic wants tool_results in a user turn; merge consecutive
                # tool messages into the same user turn.
                if out and out[-1]["role"] == "user" and isinstance(
                    out[-1]["content"], list
                ):
                    out[-1]["content"].append(block)
                else:
                    out.append({"role": "user", "content": [block]})
        return out
