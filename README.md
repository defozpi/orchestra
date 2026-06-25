# orchestra · a self-hostable agentic knowledge assistant

> **An LLM + a hand-built harness**, talking to a **real MCP server** over
> JSON-RPC, grounded by **RAG over a vector database**, extended with
> **Agent Skills**, gated by **human-in-the-loop approval**, measured by an
> **LLM-as-judge eval harness** — all in **one `docker compose up`.**

`orchestra` is a small but complete agent system. Its knowledge base is the body
of modern agentic-AI engineering itself (MCP, RAG, Agent Skills, harnesses,
A2A/A2UI), so the project doubles as a demonstration that the concepts behind it
are understood, not just name-dropped.

It is intentionally **framework-free**: the agent loop, the MCP host, the
retrieval pipeline, and the approval gate are written by hand so the moving parts
are visible — which is the whole point of a portfolio piece.

---

## What it demonstrates

| Capability | Where it lives | Idea it implements |
| --- | --- | --- |
| **Agent = LLM + harness** | [`app/harness/agent.py`](app/harness/agent.py) | The reason→act→observe loop is ~2% of the code; the harness around it (tool dispatch, approval, context budget, audit) is the rest — the "98.4% is infrastructure" insight. |
| **MCP server** | [`app/mcp_server/server.py`](app/mcp_server/server.py) | A real FastMCP server over **stdio / JSON-RPC 2.0**, with typed tool schemas and `readOnlyHint` vs. action annotations. |
| **MCP host / client** | [`app/harness/tools.py`](app/harness/tools.py) | The harness launches the server as a subprocess and discovers its tools over the protocol — exactly the local-transport pattern from the paper. |
| **RAG + vector DB** | [`app/rag/`](app/rag) | Markdown-aware chunking → local embeddings → **Qdrant** → top-k retrieval with citations. |
| **Agent Skills** | [`skills/`](skills) + [`app/skills/loader.py`](app/skills/loader.py) | `SKILL.md` folders with **progressive disclosure**: metadata always loaded, body fetched on demand via a `load_skill` tool. |
| **Human-in-the-loop** | [`app/harness/approval.py`](app/harness/approval.py) | Action (write) tools are blocked pending explicit approval — surfaced live in the UI. |
| **LLM-as-judge eval** | [`app/eval/`](app/eval) | Trigger + trajectory checks and rubric scoring with **position-swap** to neutralize ordering bias. |
| **REST + streaming API** | [`app/main.py`](app/main.py) | FastAPI with `/chat`, SSE `/chat/stream`, `/ingest`, `/health`. |
| **Web UI** | [`web/index.html`](web/index.html) | Live view of every tool call, retrieved source, and the approval gate. |
| **Provider-agnostic LLM** | [`app/llm/`](app/llm) | Claude by default; **Ollama** for fully-local; a deterministic **mock** so it runs with zero API keys. |
| **Docker** | [`docker-compose.yml`](docker-compose.yml) | api + Qdrant (+ optional Ollama) in one command. |

---

## Architecture

```
                          ┌──────────────────────────────────────────────┐
   Browser / curl  ─────► │  FastAPI  (REST + SSE)        app/main.py     │
                          │                                              │
                          │   ┌──────────────────────────────────────┐   │
                          │   │  Agent harness   app/harness/agent.py │   │
                          │   │  reason → act → observe (bounded)     │   │
                          │   │  · approval gate (HITL)               │   │
                          │   │  · context budget · audit log         │   │
                          │   └───┬───────────────┬──────────────┬────┘   │
                          │       │ LLMClient     │ ToolProvider │ Skills │
                          └───────┼───────────────┼──────────────┼────────┘
                                  │               │ (MCP stdio)  │ load_skill
                     ┌────────────▼────┐   ┌──────▼───────────┐  │
                     │ Claude / Ollama │   │  MCP server      │  │  skills/*/SKILL.md
                     │ / mock          │   │  app/mcp_server  │  │  (progressive
                     └─────────────────┘   │  · search_kb     │  │   disclosure)
                                           │  · list_documents│
                                           │  · save_note ⚠   │
                                           └──────┬───────────┘
                                                  │ RAG (app/rag)
                                           ┌──────▼───────────┐
                                           │  Qdrant (vectors)│
                                           │  fastembed (ONNX)│
                                           └──────────────────┘
```

A full request walkthrough is in [ARCHITECTURE.md](ARCHITECTURE.md).

---

## Quickstart

**Requirements:** Docker + Docker Compose. No API key needed to try it.

```bash
git clone <your-repo-url> orchestra && cd orchestra
cp .env.example .env          # optional: paste an ANTHROPIC_API_KEY for real answers
docker compose up --build     # builds, waits for Qdrant, ingests the KB, serves
```

Open **http://localhost:8000** and ask:

- *"How does MCP solve the N×M integration problem?"* → watch it retrieve & cite.
- *"Explain progressive disclosure in Agent Skills."* → watch it `load_skill`.
- *"Save this: A2UI is sheet music for UI."* → watch the **approval gate** fire.

### Three ways to run the LLM

| Mode | How | Notes |
| --- | --- | --- |
| **Claude** (default) | put `ANTHROPIC_API_KEY` in `.env` | most capable; real reasoning |
| **Mock** (zero-config) | leave the key empty | deterministic; still exercises the full loop, tools, RAG, and HITL |
| **Local / offline** | `docker compose --profile local up` then `docker compose exec ollama ollama pull llama3.1` and set `LLM_PROVIDER=ollama` | no cloud at all |

---

## Try the API directly

```bash
# health: provider, skills, MCP tools, vector count
curl -s localhost:8000/health | python -m json.tool

# one-shot chat with the audit trail
curl -s -X POST localhost:8000/chat \
  -H 'content-type: application/json' \
  -d '{"message":"How does MCP solve the N x M integration problem?","auto_approve":true}' \
  | python -m json.tool
```

## Evaluate the agent

```bash
make eval     # trigger accuracy + trajectory pass + LLM-as-judge score per case
```

The suite ([`app/eval/cases.json`](app/eval/cases.json)) is written
**evaluation-driven**: each case fixes the input, the expected tool trajectory,
and a rubric *before* the behavior — covering the trigger, execution, and
regression failure modes from the Agent Skills paper.

## Run the tests (no Docker, no network, no key)

```bash
make test     # or: pip install -r requirements-dev.txt && pytest -q
```

These exercise the harness loop, citation propagation, the HITL gate, skill
progressive disclosure, and chunking — all against the mock LLM and an in-memory
tool provider.

---

## Project layout

```
orchestra/
├── app/
│   ├── harness/        # the agent loop + tool dispatch, approval, context, audit
│   ├── llm/            # provider-agnostic LLM layer (Claude / Ollama / mock)
│   ├── mcp_server/     # the MCP server (FastMCP, stdio)
│   ├── rag/            # chunk → embed → Qdrant → retrieve
│   ├── skills/         # progressive-disclosure SKILL.md loader
│   ├── eval/           # EDD cases + LLM-as-judge + runner
│   └── main.py         # FastAPI app (REST + SSE)
├── skills/             # the Agent Skills (research-synthesis, citing-sources, note-taking)
├── knowledge_base/     # markdown the agent retrieves over
├── web/index.html      # single-page chat UI
├── tests/              # offline unit + integration tests
├── docker-compose.yml  # api + qdrant (+ optional ollama)
└── Dockerfile
```

---

## Design notes & honest limitations

- **Why no agent framework?** The brief was to show I can build an agent, so the
  loop, the MCP host, and retrieval are hand-written. In production you might
  reach for an SDK (ADK, LangGraph, the official MCP libraries) — the point here
  is that I understand what they do under the hood.
- **HITL over stateless HTTP** is modeled with an explicit approve-and-resend
  step rather than a durable approval queue; the queue is the natural next
  iteration.
- **Security posture** follows the MCP best-practices list: no hardcoded
  credentials (env only), read-only retrieval tools separated from a single
  gated write tool, and an audit log of every tool call.
- **Embeddings run locally** (fastembed / ONNX) so the demo needs no embedding
  API and works offline.

## License

MIT.
