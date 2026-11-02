"""LedgerPort interface + SQLite implementation. Same file backs both local dev and the dockerized app."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

import aiosqlite

DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "ledger.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS ledger_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id TEXT UNIQUE NOT NULL,
    vendor_id TEXT NOT NULL,
    total_amount REAL NOT NULL,
    trace_id TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


class LedgerPort(Protocol):
    async def write(self, invoice_id: str, vendor_id: str, total_amount: float, trace_id: str) -> int: ...
    async def get(self, invoice_id: str) -> dict | None: ...


class SQLiteLedger:
    """File-backed ledger: one row per compliant invoice written.

    write() is idempotent on invoice_id - re-posting the same invoice (e.g. an
    orchestrator retry after a transient notify failure) returns the existing
    ledger_id instead of raising, so a retry can never double-post.
    """

    def __init__(self, db_path: Path = DB_PATH) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    async def write(self, invoice_id: str, vendor_id: str, total_amount: float, trace_id: str) -> int:
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute(SCHEMA)
            await conn.execute(
                """
                INSERT INTO ledger_entries (invoice_id, vendor_id, total_amount, trace_id)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(invoice_id) DO NOTHING
                """,
                (invoice_id, vendor_id, total_amount, trace_id),
            )
            await conn.commit()
            cursor = await conn.execute("SELECT id FROM ledger_entries WHERE invoice_id = ?", (invoice_id,))
            row = await cursor.fetchone()
            return row[0]

    async def get(self, invoice_id: str) -> dict | None:
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute(SCHEMA)
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute("SELECT * FROM ledger_entries WHERE invoice_id = ?", (invoice_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None
