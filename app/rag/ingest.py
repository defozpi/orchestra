"""Ingestion pipeline: read knowledge base -> chunk -> embed -> store in Qdrant.

Run as a module:  python -m app.rag.ingest
"""

from __future__ import annotations

from pathlib import Path

from app.config import get_settings
from app.rag import store
from app.rag.chunking import chunk_markdown


def ingest_knowledge_base(reset: bool = True) -> dict:
    settings = get_settings()
    kb_dir = Path(settings.knowledge_base_dir)
    files = sorted(kb_dir.glob("*.md"))
    if not files:
        raise FileNotFoundError(f"No markdown files found in {kb_dir.resolve()}")

    store.ensure_collection(reset=reset)

    total_chunks = 0
    per_file = {}
    for path in files:
        text = path.read_text(encoding="utf-8")
        chunks = chunk_markdown(
            text,
            source=path.name,
            max_chars=settings.chunk_chars,
            overlap=settings.chunk_overlap,
        )
        stored = store.upsert_chunks(chunks)
        per_file[path.name] = stored
        total_chunks += stored

    return {
        "files": len(files),
        "chunks": total_chunks,
        "per_file": per_file,
        "collection": settings.qdrant_collection,
    }


if __name__ == "__main__":
    result = ingest_knowledge_base()
    print(
        f"Ingested {result['chunks']} chunks from {result['files']} files "
        f"into collection '{result['collection']}'."
    )
    for name, n in result["per_file"].items():
        print(f"  - {name}: {n} chunks")
