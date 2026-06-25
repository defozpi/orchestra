"""End-to-end harness tests using the mock LLM + fake tool provider.

No network, no API key, no Qdrant, no MCP subprocess — these exercise the
reason->act->observe loop, citations, and the HITL approval gate in isolation.
"""

from app.harness.agent import Agent
from app.harness.approval import ApprovalPolicy
from app.harness.context import trim_to_budget
from app.llm.mock_client import MockClient
from app.skills.loader import SkillRegistry
from tests.fakes import FakeToolProvider


def _agent(auto_approve=False):
    return Agent(
        llm=MockClient(),
        tools=FakeToolProvider(),
        skills=SkillRegistry.load("skills"),
        approval=ApprovalPolicy(auto_approve=auto_approve, prefixes=("save_",)),
    )


def test_question_triggers_retrieval_then_grounded_answer():
    agent = _agent()
    answer, audit = agent.run("How does MCP solve the N x M integration problem?")
    kinds = [e.kind for e in audit.events]
    assert "tool_call" in kinds and "tool_result" in kinds
    # the search tool was used and the answer cites the retrieved source
    called = [e.data["name"] for e in audit.events if e.kind == "tool_call"]
    assert "search_knowledge_base" in called
    assert "mcp.md" in answer  # citation propagated through to the answer


def test_action_tool_blocked_without_approval():
    agent = _agent(auto_approve=False)
    answer, audit = agent.run("Save this: MCP uses JSON-RPC 2.0.")
    kinds = [e.kind for e in audit.events]
    assert "approval_required" in kinds
    assert "approval" in answer.lower()
    # the action must NOT have executed
    assert not any(
        e.kind == "tool_result" and e.data["name"] == "save_note" for e in audit.events
    )


def test_action_tool_runs_with_approval():
    provider = FakeToolProvider()
    agent = Agent(
        llm=MockClient(),
        tools=provider,
        skills=SkillRegistry.load("skills"),
        approval=ApprovalPolicy(auto_approve=True, prefixes=("save_",)),
    )
    answer, audit = agent.run("Remember this: A2UI is sheet music for UI.")
    assert any(name == "save_note" for name, _ in provider.calls)
    assert "saved note" in answer.lower()


def test_context_trim_caps_growth():
    msgs = [{"role": "user", "content": "q"}]
    msgs += [{"role": "tool", "name": "t", "content": "x" * 1000} for _ in range(10)]
    msgs += [{"role": "user", "content": "latest"}]
    trimmed = trim_to_budget(msgs, max_tokens=200)
    # oldest tool results get shortened; the first user msg is preserved
    assert trimmed[0]["content"] == "q"
    assert any("[trimmed]" in m.get("content", "") for m in trimmed)
