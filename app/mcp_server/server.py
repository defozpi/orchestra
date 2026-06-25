"""orchestra-kb MCP server.

A real Model Context Protocol server exposed over the **stdio** transport: the
harness (the MCP *host*) launches this file as a subprocess and speaks JSON-RPC
2.0 over stdin/stdout — exactly the local/prototyping pattern from the whitepaper.

Tool-design choices follow the paper's best practices:
- Clear, action-oriented names (`search_knowledge_base`, not `query`).
- Rich descriptions + typed parameters (FastMCP derives the JSON input schema
  from the type hints and docstring).
- Read-only vs. action semantics: the two retrieval tools are read-only; the one
  write tool (`save_note`) has a real side effect. The MCP spec's annotation
  hints (`readOnlyHint`, etc.) are advisory only and must not be trusted from a
  server, so this distinction is documented here and *enforced host-side* by the
  harness's human-in-the-loop approval gate (it gates any tool named `save_*`).
- Descriptive error strings that tell the calling model what to do next.

Run standalone:  python -m app.mcp_server.server
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("orchestra-kb")

NOTES_DIR = Path("data/notes")


@mcp.tool()  # read-only retrieval
def search_knowledge_base(query: str, top_k: int = 4) -> str:
    """Retrieve the most relevant passages from the agentic-AI knowledge base.

    Use this whenever you need grounded facts to answer a question about MCP,
    RAG, Agent Skills, harnesses, A2A/A2UI, or related concepts. Returns the
    top matching passages, each tagged with its source filename so the answer
    can cite it. This is the agent's primary retrieval (RAG) tool.

    Args:
        query: A natural-language question or topic to search for.
        top_k: How many passages to return (1-8). Defaults to 4.

    Returns:
        Formatted passages, each prefixed with its `[source: <file>]` tag. If
        nothing relevant is found, returns a message saying so — do NOT invent
        an answer in that case.
    """
    from app.rag import store

    top_k = max(1, min(int(top_k), 8))
    try:
        hits = store.search(query, top_k=top_k)
    except Exception as exc:  # descriptive error -> the model can recover
        return (
            "ERROR: the knowledge base is unreachable or empty "
            f"({type(exc).__name__}). Make sure ingestion has run "
            "(`make ingest`) and that Qdrant is up, then retry."
        )

    if not hits:
        return (
            "No relevant passages found for that query. Tell the user the "
            "knowledge base does not cover this, or try rephrasing the search."
        )

    blocks = []
    for h in hits:
        head = f" / {h.heading}" if h.heading else ""
        blocks.append(
            f"[source: {h.source}{head}] (similarity {h.score:.2f})\n{h.text}"
        )
    return "\n\n---\n\n".join(blocks)


@mcp.tool()  # read-only
def list_documents() -> str:
    """List the source documents available in the knowledge base.

    Use this to tell the user what topics the assistant can answer about, or to
    decide whether a question is in scope before searching.

    Returns:
        A bullet list of document filenames and their first heading.
    """
    from app.config import get_settings

    kb = Path(get_settings().knowledge_base_dir)
    files = sorted(kb.glob("*.md"))
    if not files:
        return "ERROR: no knowledge-base documents found. Run `make ingest`."
    lines = []
    for f in files:
        first_heading = ""
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.startswith("#"):
                first_heading = line.lstrip("#").strip()
                break
        lines.append(f"- {f.name}: {first_heading}")
    return "Knowledge base documents:\n" + "\n".join(lines)


@mcp.tool()  # ACTION (writes a file) -> gated by the host's HITL approval
def save_note(title: str, content: str) -> str:
    """Persist a short note to disk for the user.

    This is an ACTION tool: it has a real side effect (it writes a file), so the
    host harness routes it through human-in-the-loop approval before it runs.
    Use it only when the user explicitly asks to save / remember something.

    Args:
        title: A short title for the note.
        content: The note body (one or two sentences is ideal).

    Returns:
        A confirmation with the saved note's id and path.
    """
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    note_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    payload = {
        "id": note_id,
        "title": title.strip(),
        "content": content.strip(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    path = NOTES_DIR / f"{note_id}.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return f"Saved note '{title.strip()}' with id {note_id} -> {path}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
