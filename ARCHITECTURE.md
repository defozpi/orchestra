# Architecture

This document explains how `orchestra` is put together and traces a request end
to end. It is written to be read alongside the code.

## The core idea: model vs. harness

An agent is a **model** (a remote text generator) wrapped in a **harness** (the
deterministic engineering that turns it into a reliable system). A
reverse-engineering of a production coding agent found ~98% of the code is the
harness and ~2% is the loop. `orchestra` is organized to make that split obvious:

- The loop — [`app/harness/agent.py`](app/harness/agent.py) — is short.
- Everything it relies on is a separate, testable harness module:
  - **Tool transport** ([`tools.py`](app/harness/tools.py)) — the MCP host.
  - **Approval** ([`approval.py`](app/harness/approval.py)) — the HITL gate.
  - **Context budget** ([`context.py`](app/harness/context.py)) — anti-context-rot.
  - **Audit** ([`audit.py`](app/harness/audit.py)) — every decision logged.
  - **Skills** ([`app/skills/loader.py`](app/skills/loader.py)) — procedural memory.

## Components

### LLM layer (`app/llm/`)
A neutral conversation format and an `LLMClient` protocol. Concrete clients
translate to/from each provider:
- `anthropic_client.py` — Claude (default), maps neutral messages to Anthropic
  `tool_use` / `tool_result` blocks.
- `ollama_client.py` — local models via the Ollama HTTP API.
- `mock_client.py` — a deterministic rule-based stand-in (no network) whose only
  job is to drive the harness so the whole system runs and tests with no key.

`factory.py` picks one from config and **degrades gracefully**: `anthropic` with
no key silently becomes `mock`.

### MCP server (`app/mcp_server/server.py`)
A FastMCP server exposed over **stdio**. Tools:
- `search_knowledge_base` — RAG retrieval (read-only).
- `list_documents` — what's in scope (read-only).
- `save_note` — the one **action** tool; writes to disk, so the host gates it.

Tool definitions follow the paper's best practices: action-oriented names, rich
descriptions, typed parameters (FastMCP derives the JSON schema from type hints +
docstrings), honest `readOnlyHint` annotations, and descriptive error strings
that tell the model how to recover.

### MCP host (`app/harness/tools.py`)
`McpToolProvider` launches the server as a subprocess and speaks JSON-RPC 2.0
over stdio. Because the harness is synchronous and the MCP SDK is async, the
session lives in a dedicated background thread running its own event loop;
`list_tools()` and `call()` marshal across to it. Any `ToolProvider` can be
substituted (the tests inject an in-memory fake).

### RAG (`app/rag/`)
`chunking.py` (markdown/heading-aware, dependency-free) → `embeddings.py`
(fastembed ONNX, local) → `store.py` (Qdrant: collection mgmt, upsert, cosine
search) → `ingest.py` (the pipeline). Retrieval returns passages tagged with
their source file so answers can cite them.

### Skills (`skills/` + `app/skills/loader.py`)
Each skill is a `SKILL.md` with YAML frontmatter (name, description,
allowed-tools) and a markdown body. **Progressive disclosure**: only the
metadata line is always in the system prompt; the body is fetched on demand when
the model calls the synthetic `load_skill` tool. A tiny custom frontmatter parser
keeps dependencies minimal.

### Eval (`app/eval/`)
`cases.json` are evaluation-driven cases (input, expected tools, rubric).
`run_eval.py` runs each through the agent and scores **trigger** (did the right
tool fire / stay quiet), **trajectory** (expected tools present), and **output**
via `judge.py` — an LLM-as-judge that runs twice with swapped positions to cancel
ordering bias, with a transparent heuristic fallback when no LLM is configured.

## Request lifecycle (a grounded question)

```
POST /chat {"message": "How does MCP solve the N x M problem?"}
  │
  ├─ Runtime.agent() → Agent(llm, mcp_tools, skills, approval)
  │
  ├─ system prompt = base policy + skill catalog (L1 metadata)
  ├─ tools advertised = MCP tools + load_skill
  │
  ├─ STEP 1  llm.complete(system, [user], tools)
  │            → AssistantTurn(tool_calls=[search_knowledge_base(query=…)])
  │   audit: tool_call (read-only → no approval)
  │   McpToolProvider.call → JSON-RPC over stdio → server → rag.store.search
  │            → Qdrant nearest-neighbour → passages with [source: …]
  │   audit: tool_result
  │
  ├─ STEP 2  llm.complete(system, [user, assistant, tool_result], tools)
  │            → AssistantTurn(text="… O(N+M) … [source: mcp.md]")  (no tool calls)
  │   audit: answer
  │
  └─ response: {answer, trace:[…every event…]}
```

For `save_note`, STEP 1's tool call is an **action**: if `auto_approve` is false
the harness emits `approval_required`, returns a message describing the exact
proposed call, and stops without executing. The UI shows an **Approve** button
that resends with approval granted.

## Security posture (MCP best practices)
- **No hardcoded credentials** — everything sensitive is an env var; missing keys
  degrade to mock rather than crashing.
- **Least privilege** — read-only retrieval tools are separate from the single
  gated write tool; action tools never run without approval.
- **Auditability** — every tool call and decision is recorded.
- **Local, non-production data** — the KB is shipped markdown, embeddings are
  local; nothing connects to a real production system.

## What I'd build next
- A durable approval queue (true async HITL) instead of approve-and-resend.
- Streaming tokens (not just step-level events) from Claude.
- Trace-based skill harvesting (meta-skills) and a Golden-dataset eval tier.
- A second specialist exposed over **A2A** to demonstrate multi-agent delegation.
