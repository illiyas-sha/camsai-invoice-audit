"""Agent 2 - Validation & Compliance: calls API2 then API3, produces a compliant/anomalous verdict with reasons."""

from __future__ import annotations

from typing import Awaitable, Callable

from agents.mcp_client import MCPToolClient, MCPToolError
from agents.state import InvoiceAuditState


def build_agent2(client: MCPToolClient) -> Callable[[InvoiceAuditState], Awaitable[dict]]:
    """Build the Agent 2 node: look up the contract threshold (API2), then apply policy (API3)."""

    async def agent2_validation(state: InvoiceAuditState) -> dict:
        invoice = state["invoice"]

        try:
            thresholds = await client.call(
                "vector_knowledge",
                vendor_id=invoice["vendor_id"],
                vendor_name=invoice["vendor_name"],
            )
            verdict = await client.call(
                "policy_check",
                line_items=invoice["line_items"],
                total_amount=invoice["total_amount"],
                rate_ceiling=thresholds["rate_ceiling"],
                total_billing_cap=thresholds["total_billing_cap"],
            )
        except MCPToolError as exc:
            return {"error": f"Agent 2 compliance check failed: {exc.message}"}

        return {
            "is_compliant": verdict["is_compliant"],
            "compliance_reasons": verdict["reasons"],
        }

    return agent2_validation
