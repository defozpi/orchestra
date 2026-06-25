#!/usr/bin/env bash
# Container entrypoint: wait for Qdrant, build the index, then serve the API.
set -euo pipefail

echo "[entrypoint] waiting for Qdrant at ${QDRANT_URL:-http://qdrant:6333} ..."
python scripts/wait_for_qdrant.py

echo "[entrypoint] ingesting knowledge base into the vector store ..."
python -m app.rag.ingest || echo "[entrypoint] ingest failed; the API will still start (use POST /ingest to retry)."

echo "[entrypoint] starting API on :${API_PORT:-8000}"
exec uvicorn app.main:app --host "${API_HOST:-0.0.0.0}" --port "${API_PORT:-8000}"
