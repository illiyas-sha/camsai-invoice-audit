"""Shared LangGraph state: raw_payload, invoice, verdict, ledger_id, notification_status, error, trace_id.

A plain TypedDict with total=False, matching LangGraph's convention: every
node returns a partial dict of only the fields it updates, and the graph
merges that into the running state.
"""

from __future__ import annotations

from typing import Any, TypedDict


class InvoiceAuditState(TypedDict, total=False):
    invoice_id: str
    trace_id: str

    raw_payload: dict[str, Any]
    invoice: dict[str, Any]

    is_compliant: bool
    compliance_reasons: list[str]

    ledger_id: int
    notification_sent: bool

    error: str
