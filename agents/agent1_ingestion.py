"""Agent 1 - Ingestion & Extraction: calls API1, parses into the Invoice schema, routes malformed payloads to the error state."""

from __future__ import annotations

from typing import Awaitable, Callable

from pydantic import ValidationError

from agents.mcp_client import MCPToolClient, MCPToolError
from agents.state import InvoiceAuditState
from mock_data.models import Invoice


def build_agent1(client: MCPToolClient) -> Callable[[InvoiceAuditState], Awaitable[dict]]:
    """Build the Agent 1 node: fetch the raw payload (API1), then extract/validate it."""

    async def agent1_ingestion(state: InvoiceAuditState) -> dict:
        invoice_id = state["invoice_id"]

        try:
            raw_payload = await client.call("fetch_payload", invoice_id=invoice_id)
        except MCPToolError as exc:
            return {"error": f"Agent 1 fetch failed: {exc.message}"}

        try:
            invoice = Invoice.model_validate(raw_payload)
        except ValidationError as exc:
            return {"raw_payload": raw_payload, "error": f"Agent 1 extraction failed: {exc}"}

        return {"raw_payload": raw_payload, "invoice": invoice.model_dump(mode="json")}

    return agent1_ingestion
