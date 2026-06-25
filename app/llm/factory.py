"""Select the LLM provider from config, with graceful degradation.

If the configured provider is unavailable (e.g. ANTHROPIC_API_KEY missing), fall
back to the deterministic mock so the stack always runs — a reviewer never hits
a crash for lack of a secret.
"""

from __future__ import annotations

import logging

from app.config import get_settings
from app.llm.base import LLMClient
from app.llm.mock_client import MockClient

logger = logging.getLogger("orchestra.llm")


def build_llm() -> LLMClient:
    settings = get_settings()
    provider = settings.llm_provider

    if provider == "anthropic":
        if not settings.anthropic_api_key:
            logger.warning(
                "LLM_PROVIDER=anthropic but ANTHROPIC_API_KEY is unset; "
                "falling back to the deterministic mock LLM."
            )
            return MockClient()
        from app.llm.anthropic_client import AnthropicClient

        return AnthropicClient()

    if provider == "ollama":
        from app.llm.ollama_client import OllamaClient

        return OllamaClient()

    return MockClient()
