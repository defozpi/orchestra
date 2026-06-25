"""Qdrant vector store wrapper: collection management, upsert, and search."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from functools import lru_cache

from app.config import get_settings
from app.rag.chunking import Chunk
from app.rag.embeddings import embed_query, embed_texts


@dataclass
class Retrieved:
    text: str
    source: str
    heading: str
    score: float


@lru_cache
def _client():
    from qdrant_client import QdrantClient

    return QdrantClient(url=get_settings().qdrant_url)


def ensure_collection(reset: bool = False) -> None:
    from qdrant_client import models

    settings = get_settings()
    client = _client()
    exists = client.collection_exists(settings.qdrant_collection)
    if exists and reset:
        client.delete_collection(settings.qdrant_collection)
        exists = False
    if not exists:
        client.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=models.VectorParams(
                size=settings.embedding_dim,
                distance=models.Distance.COSINE,
            ),
        )


def upsert_chunks(chunks: list[Chunk]) -> int:
    """Embed and store a batch of chunks. Returns the number stored."""
    from qdrant_client import models

    if not chunks:
        return 0

    settings = get_settings()
    vectors = embed_texts([c.text for c in chunks])
    points = [
        models.PointStruct(
            id=str(uuid.uuid4()),
            vector=vec,
            payload={
                "text": c.text,
                "source": c.source,
                "heading": c.heading,
                "index": c.index,
            },
        )
        for c, vec in zip(chunks, vectors)
    ]
    _client().upsert(collection_name=settings.qdrant_collection, points=points)
    return len(points)


def search(query: str, top_k: int | None = None) -> list[Retrieved]:
    """Nearest-neighbour search over the knowledge base."""
    settings = get_settings()
    k = top_k or settings.retrieval_top_k
    hits = _client().query_points(
        collection_name=settings.qdrant_collection,
        query=embed_query(query),
        limit=k,
        with_payload=True,
    ).points
    return [
        Retrieved(
            text=h.payload["text"],
            source=h.payload["source"],
            heading=h.payload.get("heading", ""),
            score=h.score,
        )
        for h in hits
    ]


def count() -> int:
    settings = get_settings()
    try:
        return _client().count(settings.qdrant_collection).count
    except Exception:
        return 0
