"""Agent 3 - Reporting & Settlement: ledger_write / success-notify on compliant, escalation-notify on anomalous, error-notify on failure.

Three separate node factories, one per route, wired by the orchestrator's
conditional edges rather than branching inside a single function.
"""

from __future__ import annotations

from typing import Awaitable, Callable

from agents.mcp_client import MCPToolClient, MCPToolError
from agents.state import InvoiceAuditState


def build_agent3_post_and_notify(client: MCPToolClient) -> Callable[[InvoiceAuditState], Awaitable[dict]]:
    """Compliant route: write to the ledger (API4), then send a success notification (API5)."""

    async def agent3_post_and_notify(state: InvoiceAuditState) -> dict:
        invoice = state["invoice"]
        try:
            ledger_result = await client.call(
                "ledger_write",
                invoice_id=invoice["invoice_id"],
                vendor_id=invoice["vendor_id"],
                total_amount=invoice["total_amount"],
                trace_id=state.get("trace_id", "unknown"),
            )
            await client.call(
                "notify",
                level="success",
                subject=f"Invoice {invoice['invoice_id']} posted to ledger",
                body=f"Vendor: {invoice['vendor_name']} \n invoice for {invoice['total_amount']} was compliant and posted.",
            )
        except MCPToolError as exc:
            return {"error": f"Agent 3 ledger/notify failed: {exc.message}"}

        return {"ledger_id": ledger_result["ledger_id"], "notification_sent": True}

    return agent3_post_and_notify


def build_agent3_escalate(client: MCPToolClient) -> Callable[[InvoiceAuditState], Awaitable[dict]]:
    """Anomalous route: skip the ledger entirely, send an escalation notification."""

    async def agent3_escalate(state: InvoiceAuditState) -> dict:
        invoice = state["invoice"]
        reasons = "; ".join(state.get("compliance_reasons", []))
        try:
            await client.call(
                "notify",
                level="escalation",
                subject=f"Invoice {invoice['invoice_id']} flagged for review",
                body=f"Vendor: {invoice['vendor_name']} \n\n invoice breached policy: {reasons}",
            )
        except MCPToolError as exc:
            return {"error": f"Agent 3 escalation notify failed: {exc.message}"}

        return {"notification_sent": True}

    return agent3_escalate


def build_agent3_error_notify(client: MCPToolClient) -> Callable[[InvoiceAuditState], Awaitable[dict]]:
    """Failure route: notify that this invoice could not be processed, without crashing the run."""

    async def agent3_error_notify(state: InvoiceAuditState) -> dict:
        invoice_id = state.get("invoice_id") or (state.get("raw_payload") or {}).get("invoice_id") or "unknown"
        error = state.get("error", "unknown error")
        try:
            await client.call("notify", level="error", subject=f"Invoice {invoice_id} failed processing", body=error)
        except MCPToolError:
            # Best-effort: the run already failed upstream; a second failure
            # here must not mask the original error or crash the orchestrator.
            pass

        return {"notification_sent": True}

    return agent3_error_notify
