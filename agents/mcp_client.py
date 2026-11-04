"""Spawns mcp_server over stdio and exposes a call_tool(name, **kwargs) helper for the agent nodes.

One MCPToolClient instance is shared by all three agents for the lifetime of
a single orchestrator run: the server subprocess is spawned once, reused for
every tool call, and torn down when the run finishes.
"""

from __future__ import annotations

import json
import os
import sys
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class MCPToolError(Exception):
    """Raised when an MCP tool call comes back with is_error=True."""

    def __init__(self, tool_name: str, message: str) -> None:
        self.tool_name = tool_name
        self.message = message
        super().__init__(f"MCP tool '{tool_name}' failed: {message}")


class MCPToolClient:
    """Async context manager wrapping one stdio-spawned MCP server session."""

    def __init__(self) -> None:
        self._stack = AsyncExitStack()
        self._session: ClientSession | None = None

    async def __aenter__(self) -> "MCPToolClient":
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "mcp_server.server"],
            cwd=str(PROJECT_ROOT),
            # The SDK only forwards a security-curated env allowlist (PATH,
            # APPDATA, ...) to the spawned server by default - NOTIFIER_BACKEND,
            # SMTP_*, and ANTHROPIC_API_KEY would silently never reach it.
            # Pass the full parent environment through explicitly instead.
            env=os.environ.copy(),
        )
        read, write = await self._stack.enter_async_context(stdio_client(params))
        self._session = await self._stack.enter_async_context(ClientSession(read, write))
        await self._session.initialize()
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self._stack.aclose()

    async def call(self, tool_name: str, **arguments: Any) -> dict:
        """Call an MCP tool and return its result as a plain dict, or raise MCPToolError."""
        if self._session is None:
            raise RuntimeError("MCPToolClient used outside its 'async with' block")

        result = await self._session.call_tool(tool_name, arguments)

        if result.is_error:
            message = result.content[0].text if result.content else "unknown error"
            raise MCPToolError(tool_name, message)

        if result.structured_content is not None:
            return result.structured_content
        return json.loads(result.content[0].text)
