"""The agent loop — LLM + harness.

This is the ~2% (the reason -> act -> observe loop). Everything it leans on —
tool discovery over MCP, the HITL approval gate, context budgeting, the skill
catalog, the audit log — is the ~98% that makes it reliable.

Flow per user message:
  1. Build the system prompt: base policy + the Agent Skills catalog (L1).
  2. Advertise tools = MCP tools + a synthetic `load_skill` tool.
  3. Loop (bounded): ask the model; if it calls tools, execute them (gating
     action tools through approval, serving skill bodies for `load_skill`),
     feed results back, and continue; otherwise return the final answer.

`run_stream` yields AuditEvents as they happen (for SSE); `run` consumes the
stream and returns the final answer plus the full audit trail.
"""

from __future__ import annotations

from typing import Any, Iterator

from app.config import Settings, get_settings
from app.harness.approval import ApprovalPolicy
from app.harness.audit import AuditEvent, AuditLog
from app.harness.context import trim_to_budget
from app.harness.tools import ToolProvider
from app.llm.base import AssistantTurn, LLMClient, ToolSpec
from app.skills.loader import SkillRegistry

LOAD_SKILL_TOOL = ToolSpec(
    name="load_skill",
    description=(
        "Load the full step-by-step instructions for one of the installed Agent "
        "Skills, by name. Call this BEFORE doing the work whenever a skill from "
        "the 'Available skills' catalog matches the user's request. Progressive "
        "disclosure: only the loaded skill's body enters context."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "The skill name exactly as it appears in the catalog.",
            }
        },
        "required": ["name"],
    },
)

BASE_SYSTEM_PROMPT = """You are orchestra, a grounded knowledge assistant for \
agentic-AI engineering concepts (MCP, RAG, Agent Skills, harnesses, A2A/A2UI).

Operating rules:
- Answer ONLY from the knowledge base. Use the search_knowledge_base tool to \
retrieve evidence before making factual claims; never invent facts.
- When a skill in the catalog below matches the task, call load_skill first and \
follow its workflow.
- Cite sources inline as [source: <file>] using the source tags the search tool \
returns, and finish grounded answers with a short "Sources:" list.
- If retrieval finds nothing relevant, say so plainly instead of guessing.
- Keep answers tight and useful.

Available skills (call load_skill to get a skill's full instructions):
{skill_catalog}
"""


class Agent:
    def __init__(
        self,
        llm: LLMClient,
        tools: ToolProvider,
        skills: SkillRegistry,
        approval: ApprovalPolicy,
        settings: Settings | None = None,
    ) -> None:
        self.llm = llm
        self.tools = tools
        self.skills = skills
        self.approval = approval
        self.settings = settings or get_settings()

    # -- public API ------------------------------------------------------
    def run(self, user_message: str) -> tuple[str, AuditLog]:
        audit = AuditLog()
        answer = ""
        for event in self.run_stream(user_message, audit):
            if event.kind == "answer":
                answer = event.data.get("text", "")
        return answer, audit

    def run_stream(
        self, user_message: str, audit: AuditLog | None = None
    ) -> Iterator[AuditEvent]:
        audit = audit or AuditLog()
        system = BASE_SYSTEM_PROMPT.format(skill_catalog=self.skills.catalog())
        advertised = self.tools.list_tools() + [LOAD_SKILL_TOOL]
        messages: list[dict[str, Any]] = [{"role": "user", "content": user_message}]

        yield audit.record("step", n=0, provider=self.llm.name, tools=len(advertised))

        for step in range(1, self.settings.max_agent_steps + 1):
            messages = trim_to_budget(messages, self.settings.max_context_tokens)
            turn: AssistantTurn = self.llm.complete(system, messages, advertised)

            if not turn.wants_tools:
                text = turn.text or "(no answer produced)"
                yield audit.record("answer", text=text, steps=step)
                return

            # record the assistant turn (prose + tool calls) in history
            messages.append(
                {"role": "assistant", "text": turn.text, "tool_calls": turn.tool_calls}
            )

            for call in turn.tool_calls:
                is_action = self.approval.is_action(call.name)
                yield audit.record(
                    "tool_call",
                    id=call.id,
                    name=call.name,
                    arguments=call.arguments,
                    is_action=is_action,
                )

                # HITL gate: stop before executing an unapproved action tool.
                if self.approval.needs_approval(call.name):
                    yield audit.record(
                        "approval_required", name=call.name, arguments=call.arguments
                    )
                    msg = (
                        f"This action needs your approval before it runs.\n\n"
                        f"Proposed call: `{call.name}` with "
                        f"{_fmt_args(call.arguments)}\n\n"
                        "Approve it to proceed (in the UI, click Approve; via the "
                        "API, resend with \"auto_approve\": true)."
                    )
                    yield audit.record("answer", text=msg, steps=step, pending_approval=True)
                    return

                result_text = self._dispatch(call.name, call.arguments, audit)
                yield audit.record("tool_result", name=call.name, content=result_text)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "name": call.name,
                        "content": result_text,
                    }
                )

        yield audit.record(
            "answer",
            text="I reached the step limit before finishing. Try a more specific question.",
            steps=self.settings.max_agent_steps,
            truncated=True,
        )

    # -- tool dispatch ---------------------------------------------------
    def _dispatch(self, name: str, arguments: dict[str, Any], audit: AuditLog) -> str:
        if name == LOAD_SKILL_TOOL.name:
            skill_name = arguments.get("name", "")
            body = self.skills.get_body(skill_name)
            if body is None:
                return (
                    f"No skill named '{skill_name}'. Available: "
                    f"{', '.join(s.name for s in self.skills.skills)}."
                )
            audit.record("skill_loaded", name=skill_name)
            return f"# Skill loaded: {skill_name}\n\n{body}"
        try:
            return self.tools.call(name, arguments)
        except Exception as exc:
            return f"TOOL ERROR calling {name}: {type(exc).__name__}: {exc}"


def _fmt_args(arguments: dict[str, Any]) -> str:
    return ", ".join(f"{k}={v!r}" for k, v in arguments.items()) or "(no arguments)"
