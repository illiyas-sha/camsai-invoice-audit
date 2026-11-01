"""Shared Pydantic schema: LineItem / Invoice. The one contract every agent and API agrees on.

Only structural invariants live here (positive numbers, non-empty line items).
Business policy (rate ceilings, billing caps) is Agent 2 / API3's job, not the
schema's — Scenario B must pass this validation and still get flagged later.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class LineItem(BaseModel):
    description: str
    quantity: float = Field(gt=0)
    unit_rate: float = Field(gt=0)
    line_total: float = Field(gt=0)


class Invoice(BaseModel):
    invoice_id: str
    vendor_id: str
    vendor_name: str
    invoice_date: date
    currency: str = "USD"
    line_items: list[LineItem] = Field(min_length=1)
    total_amount: float = Field(gt=0)
