"""Process-wide agent runtime.

Holds the expensive, long-lived pieces — the LLM client, the loaded skill
registry, and the live MCP host connection (a subprocess kept open for the
lifetime of the API) — and hands out a per-request `Agent` with the right
approval policy.
"""

from __future__ import annotations

import logging

from app.config import get_settings
from app.harness.agent import Agent
from app.harness.approval import ApprovalPolicy
from app.harness.tools import McpToolProvider
from app.llm.factory import build_llm
from app.skills.loader import SkillRegistry

logger = logging.getLogger("orchestra.runtime")


class Runtime:
    def __init__(self) -> None:
        settings = get_settings()
        self.settings = settings
        self.llm = build_llm()
        self.skills = SkillRegistry.load()
        logger.info(
            "runtime: provider=%s skills=%d", self.llm.name, len(self.skills.skills)
        )
        self.tools = McpToolProvider(
            command=settings.mcp_command, args=settings.mcp_args
        ).start()
        logger.info(
            "runtime: connected to MCP server, %d tools: %s",
            len(self.tools.list_tools()),
            ", ".join(t.name for t in self.tools.list_tools()),
        )

    def agent(self, auto_approve: bool = False) -> Agent:
        return Agent(
            llm=self.llm,
            tools=self.tools,
            skills=self.skills,
            approval=ApprovalPolicy.from_settings(auto_approve=auto_approve),
            settings=self.settings,
        )

    def close(self) -> None:
        self.tools.close()
