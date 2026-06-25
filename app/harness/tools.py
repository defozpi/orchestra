"""Tool provider abstraction + the MCP (stdio) implementation.

The harness is the MCP *host*: it launches the MCP server as a local subprocess
and speaks JSON-RPC 2.0 over stdio (`mcp` SDK). Because the rest of the harness
is synchronous, the async MCP session is owned by a dedicated background thread
running its own event loop; sync `list_tools()` / `call()` marshal across to it.

Any object satisfying `ToolProvider` can be dropped in (tests use a fake one),
which keeps the agent loop decoupled from the transport.
"""

from __future__ import annotations

import asyncio
import os
import threading
from typing import Any, Protocol

from app.llm.base import ToolSpec


class ToolProvider(Protocol):
    def list_tools(self) -> list[ToolSpec]: ...
    def call(self, name: str, arguments: dict[str, Any]) -> str: ...
    def close(self) -> None: ...


class McpToolProvider:
    """Connects to an MCP server over stdio and exposes its tools synchronously."""

    def __init__(
        self,
        command: str,
        args: tuple[str, ...] | list[str],
        env: dict[str, str] | None = None,
        startup_timeout: float = 30.0,
        call_timeout: float = 60.0,
    ) -> None:
        self._command = command
        self._args = list(args)
        self._env = env if env is not None else dict(os.environ)
        self._startup_timeout = startup_timeout
        self._call_timeout = call_timeout

        self._loop: asyncio.AbstractEventLoop | None = None
        self._session = None
        self._stop_event: asyncio.Event | None = None
        self._tools: list[ToolSpec] = []
        self._ready = threading.Event()
        self._error: Exception | None = None
        self._thread: threading.Thread | None = None

    # -- lifecycle -------------------------------------------------------
    def start(self) -> "McpToolProvider":
        self._thread = threading.Thread(target=self._run, name="mcp-host", daemon=True)
        self._thread.start()
        if not self._ready.wait(timeout=self._startup_timeout):
            raise TimeoutError("MCP server did not become ready in time")
        if self._error:
            raise self._error
        return self

    def _run(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._main())
        except Exception as exc:  # pragma: no cover - surfaced via _error
            self._error = exc
            self._ready.set()

    async def _main(self) -> None:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        params = StdioServerParameters(
            command=self._command, args=self._args, env=self._env
        )
        try:
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    self._session = session
                    self._stop_event = asyncio.Event()
                    listed = await session.list_tools()
                    self._tools = [
                        ToolSpec(
                            name=t.name,
                            description=t.description or "",
                            input_schema=t.inputSchema or {"type": "object", "properties": {}},
                        )
                        for t in listed.tools
                    ]
                    self._ready.set()
                    await self._stop_event.wait()
        except Exception as exc:
            self._error = exc
            self._ready.set()
            raise

    # -- sync API --------------------------------------------------------
    def list_tools(self) -> list[ToolSpec]:
        return list(self._tools)

    def call(self, name: str, arguments: dict[str, Any]) -> str:
        if self._loop is None:
            raise RuntimeError("MCP provider not started")
        future = asyncio.run_coroutine_threadsafe(
            self._call(name, arguments), self._loop
        )
        return future.result(timeout=self._call_timeout)

    async def _call(self, name: str, arguments: dict[str, Any]) -> str:
        result = await self._session.call_tool(name, arguments)
        parts: list[str] = []
        for block in result.content:
            text = getattr(block, "text", None)
            if text is not None:
                parts.append(text)
        out = "\n".join(parts).strip()
        if getattr(result, "isError", False):
            return f"TOOL ERROR: {out}" if out else "TOOL ERROR (no detail)"
        return out or "(tool returned no content)"

    def close(self) -> None:
        if self._loop and self._stop_event:
            self._loop.call_soon_threadsafe(self._stop_event.set)
        if self._thread:
            self._thread.join(timeout=5)
