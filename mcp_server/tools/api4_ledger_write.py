"""API 4 - Ledger Write: persists a compliant invoice to the SQLite ledger store."""

from __future__ import annotations

from mcp_server.ledger.sqlite_store import SQLiteLedger

_ledger = SQLiteLedger()


async def ledger_write(invoice_id: str, vendor_id: str, total_amount: float, trace_id: str) -> dict:
    """Write a compliant invoice to the ledger. Returns the new ledger row id."""
    row_id = await _ledger.write(invoice_id, vendor_id, total_amount, trace_id)
    return {"ledger_id": row_id}
