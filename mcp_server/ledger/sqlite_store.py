"""LedgerPort interface + SQLite implementation. Same file backs both local dev and the dockerized app."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

import aiosqlite

DB_PATH = Path(__file__).resolve().parent.parent.parent / "ledger.db"

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
    """File-backed ledger: one row per compliant invoice written."""

    def __init__(self, db_path: Path = DB_PATH) -> None:
        self.db_path = db_path

    async def write(self, invoice_id: str, vendor_id: str, total_amount: float, trace_id: str) -> int:
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute(SCHEMA)
            cursor = await conn.execute(
                "INSERT INTO ledger_entries (invoice_id, vendor_id, total_amount, trace_id) VALUES (?, ?, ?, ?)",
                (invoice_id, vendor_id, total_amount, trace_id),
            )
            await conn.commit()
            return cursor.lastrowid

    async def get(self, invoice_id: str) -> dict | None:
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute(SCHEMA)
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute("SELECT * FROM ledger_entries WHERE invoice_id = ?", (invoice_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None
