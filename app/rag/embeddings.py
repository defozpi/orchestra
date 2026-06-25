"""Local embedding model via fastembed (ONNX).

Runs fully offline — no API key, no torch, no GPU. The model is downloaded once
and cached. Loading is lazy so importing this module is cheap and the unit tests
don't pull in the heavy dependency.
"""

from __future__ import annotations

from functools import lru_cache

from app.config import get_settings


@lru_cache
def _model():
    from fastembed import TextEmbedding  # imported lazily on first use

    settings = get_settings()
    return TextEmbedding(model_name=settings.embedding_model)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts into vectors."""
    return [vec.tolist() for vec in _model().embed(texts)]


def embed_query(text: str) -> list[float]:
    """Embed a single query string."""
    return embed_texts([text])[0]
