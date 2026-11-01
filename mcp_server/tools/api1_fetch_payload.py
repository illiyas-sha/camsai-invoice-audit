"""API 1 - Fetch Payload: given an invoice_id, reads the matching raw JSON from mock_data/inbox/."""

from __future__ import annotations

import json
from pathlib import Path

INBOX_DIR = Path(__file__).resolve().parent.parent.parent / "mock_data" / "inbox"


async def fetch_payload(invoice_id: str) -> dict:
    """Fetch the raw invoice payload for invoice_id from the inbox.

    Returns the payload exactly as it arrived - no validation here. API1 only
    retrieves; Agent 1 is responsible for extracting and validating it.
    """
    path = INBOX_DIR / f"{invoice_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"No payload found for invoice_id={invoice_id!r} in {INBOX_DIR}")
    return json.loads(path.read_text())
