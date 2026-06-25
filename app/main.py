"""FastAPI application: REST + SSE chat over the agent harness.

Endpoints
  GET  /health        -> liveness + provider / KB status
  POST /ingest        -> (re)build the vector index from knowledge_base/
  POST /chat          -> non-streaming agent answer + full audit trail
  GET  /chat/stream   -> Server-Sent Events: live tool calls, approvals, answer
  GET  /              -> the single-page chat UI
"""

from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from app import __version__
from app.config import get_settings
from app.harness.runtime import Runtime

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("orchestra.api")

WEB_DIR = Path("web")


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.runtime = Runtime()
    try:
        yield
    finally:
        app.state.runtime.close()


app = FastAPI(title="orchestra", version=__version__, lifespan=lifespan)


class ChatRequest(BaseModel):
    message: str
    auto_approve: bool = False


@app.get("/health")
def health() -> JSONResponse:
    from app.rag import store

    settings = get_settings()
    runtime: Runtime = app.state.runtime
    return JSONResponse(
        {
            "status": "ok",
            "version": __version__,
            "llm_provider": runtime.llm.name,
            "skills": [s.name for s in runtime.skills.skills],
            "mcp_tools": [t.name for t in runtime.tools.list_tools()],
            "kb_vectors": store.count(),
            "collection": settings.qdrant_collection,
        }
    )


@app.post("/ingest")
def ingest() -> JSONResponse:
    from app.rag.ingest import ingest_knowledge_base

    try:
        result = ingest_knowledge_base(reset=True)
        return JSONResponse({"status": "ok", **result})
    except Exception as exc:
        logger.exception("ingest failed")
        return JSONResponse(
            {"status": "error", "error": f"{type(exc).__name__}: {exc}"},
            status_code=500,
        )


@app.post("/chat")
def chat(req: ChatRequest) -> JSONResponse:
    runtime: Runtime = app.state.runtime
    agent = runtime.agent(auto_approve=req.auto_approve)
    answer, audit = agent.run(req.message)
    return JSONResponse(
        {"answer": answer, "trace": [e.as_dict() for e in audit.events]}
    )


@app.get("/chat/stream")
def chat_stream(message: str, auto_approve: bool = False) -> EventSourceResponse:
    runtime: Runtime = app.state.runtime
    agent = runtime.agent(auto_approve=auto_approve)

    def event_generator():
        for event in agent.run_stream(message):
            yield {"event": event.kind, "data": json.dumps(event.as_dict())}

    return EventSourceResponse(event_generator())


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")
