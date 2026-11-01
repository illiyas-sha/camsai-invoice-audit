"""MCPServer app: registers API1-API5 as MCP tools, served over stdio for local agent clients.

Note: in mcp SDK 2.x the high-level helper class was renamed from FastMCP to
MCPServer (import path: mcp.server.mcpserver.MCPServer). Behavior is the same
decorator-based tool registration; only the name/import changed from the 1.x
docs most tutorials still reference.
"""

from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from mcp_server.tools.api1_fetch_payload import fetch_payload
from mcp_server.tools.api2_vector_knowledge import vector_knowledge
from mcp_server.tools.api3_policy_check import policy_check
from mcp_server.tools.api4_ledger_write import ledger_write
from mcp_server.tools.api5_notify import notify

mcp = MCPServer("camsai-invoice-audit")

mcp.tool()(fetch_payload)
mcp.tool()(vector_knowledge)
mcp.tool()(policy_check)
mcp.tool()(ledger_write)
mcp.tool()(notify)


if __name__ == "__main__":
    mcp.run(transport="stdio")
