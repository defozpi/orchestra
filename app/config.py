"""Central, environment-driven configuration.

Whitepaper tie-in (MCP security best practices): credentials are *never*
hardcoded. Everything sensitive arrives through environment variables, and the
app degrades gracefully when a key is absent (it falls back to a local or mock
LLM) so a reviewer can run the whole stack with zero secrets.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

LLMProvider = Literal["anthropic", "ollama", "mock"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- LLM selection ---------------------------------------------------
    # Default provider. If "anthropic" is selected but no API key is present,
    # the factory automatically downgrades to "mock" so nothing crashes.
    llm_provider: LLMProvider = Field(default="anthropic")
    anthropic_api_key: Optional[str] = Field(default=None)
    anthropic_model: str = Field(default="claude-opus-4-8")

    ollama_base_url: str = Field(default="http://ollama:11434")
    ollama_model: str = Field(default="llama3.1")

    # --- Agent harness ---------------------------------------------------
    max_agent_steps: int = Field(default=6)  # bound on the reason->act loop
    max_context_tokens: int = Field(default=12000)  # soft budget (see context.py)
    temperature: float = Field(default=0.2)

    # HITL: tools whose name starts with one of these prefixes require human
    # approval before they execute (see harness/approval.py).
    require_approval_prefixes: tuple[str, ...] = ("save_", "delete_", "send_")

    # --- RAG / vector DB -------------------------------------------------
    qdrant_url: str = Field(default="http://qdrant:6333")
    qdrant_collection: str = Field(default="orchestra_kb")
    embedding_model: str = Field(default="BAAI/bge-small-en-v1.5")
    embedding_dim: int = Field(default=384)
    chunk_chars: int = Field(default=1100)
    chunk_overlap: int = Field(default=180)
    retrieval_top_k: int = Field(default=4)
    knowledge_base_dir: str = Field(default="knowledge_base")

    # --- Skills ----------------------------------------------------------
    skills_dir: str = Field(default="skills")

    # --- MCP -------------------------------------------------------------
    # How the harness launches the MCP server (stdio transport — the host
    # spawns the server as a local subprocess, exactly as the whitepaper
    # describes for local/prototyping use).
    mcp_command: str = Field(default="python")
    mcp_args: tuple[str, ...] = ("-m", "app.mcp_server.server")

    # --- API -------------------------------------------------------------
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)


@lru_cache
def get_settings() -> Settings:
    return Settings()
