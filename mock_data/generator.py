"""Faker-based generator: writes scenario_a (compliant), scenario_b (anomalous), scenario_c (malformed) to mock_data/inbox/.

Run via `python -m mock_data.generator`. All three scenarios share VENDOR_ID /
CONTRACT_RATE_CEILING with mcp_server/vectorstore/seed_contracts.py so API2's
Chroma lookup and these fixtures agree on the same historical contract.

Assessment Instruction for generator:
Required Structural Scenarios: Your generator must automatically output at least three distinct testing profiles to validate your Orchestrator’s conditional branching behavior:

Scenario A (Fully Compliant): A standard invoice containing well-formed line items that sit perfectly within your historical vector contracts ($4,000 threshold) and total billings under $50,000. (Expected: Route to Ledger -> Complete).
Scenario B (Anomalous Rate/Price Deviation): An invoice matching the schema below where a single line-item unit rate violates contract thresholds. (Expected: Trigger Agent 2 Flag -> Skip Ledger -> Route to Slack Escalation).
Scenario C (Structural Engine Crash): A malformed payload containing negative numerical values, empty line item arrays, or corrupted strings. (Expected: Validate orchestrator's state recovery, graceful exception management, and immediate error reporting without hanging).

"""

from __future__ import annotations

import json
from pathlib import Path

from faker import Faker

from mock_data.models import Invoice, LineItem

INBOX_DIR = Path(__file__).parent / "inbox"

VENDOR_ID = "VEND-001"
VENDOR_NAME = "Acme Industrial Supplies Inc."
CONTRACT_RATE_CEILING = 4000.0  # per-unit rate ceiling from the historical contract
TOTAL_BILLING_CAP = 50000.0

fake = Faker()
Faker.seed(42)


def _write(invoice_id: str, payload: dict) -> Path:
    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    path = INBOX_DIR / f"{invoice_id}.json"
    path.write_text(json.dumps(payload, indent=2, default=str))
    return path


def build_scenario_a() -> dict:
    """Fully compliant: every rate under the contract ceiling, total under the billing cap."""
    invoice = Invoice(
        invoice_id="INV-A-0001",
        vendor_id=VENDOR_ID,
        vendor_name=VENDOR_NAME,
        invoice_date=fake.date_this_year(),
        currency="USD",
        line_items=[
            LineItem(description="Industrial sensors (batch)", quantity=3, unit_rate=1200.0, line_total=3600.0),
            LineItem(description="Maintenance service", quantity=2, unit_rate=950.0, line_total=1900.0),
            LineItem(description="Replacement parts kit", quantity=4, unit_rate=800.0, line_total=3200.0),
        ],
        total_amount=3600.0 + 1900.0 + 3200.0,
    )
    return invoice.model_dump(mode="json")


def build_scenario_b() -> dict:
    """Anomalous: one line item's unit rate breaches the $4,000 contract ceiling."""
    invoice = Invoice(
        invoice_id="INV-B-0001",
        vendor_id=VENDOR_ID,
        vendor_name=VENDOR_NAME,
        invoice_date=fake.date_this_year(),
        currency="USD",
        line_items=[
            LineItem(description="Industrial sensors (batch)", quantity=3, unit_rate=1200.0, line_total=3600.0),
            LineItem(description="Emergency repair labor", quantity=1, unit_rate=6500.0, line_total=6500.0),
            LineItem(description="Replacement parts kit", quantity=4, unit_rate=800.0, line_total=3200.0),
        ],
        total_amount=3600.0 + 6500.0 + 3200.0,
    )
    return invoice.model_dump(mode="json")


def build_scenario_c() -> dict:
    """Structurally malformed: empty line items + a corrupted total.

    Built as a raw dict, bypassing the Invoice model entirely, because the
    whole point of this fixture is that it must fail Agent 1's extraction
    step rather than arrive pre-validated.
    """
    return {
        "invoice_id": "INV-C-0001",
        "vendor_id": VENDOR_ID,
        "vendor_name": VENDOR_NAME,
        "invoice_date": str(fake.date_this_year()),
        "currency": "USD",
        "line_items": [],
        "total_amount": "not-a-number",
    }


def build_scenario_d() -> dict:
    """Anomalous on the OTHER rule: every rate stays under the $4,000 ceiling,
    but the total crosses the $50,000 billing cap - exercises policy_check's
    total_billing_cap branch, which A/B/C never reach.
    """
    invoice = Invoice(
        invoice_id="INV-D-0001",
        vendor_id=VENDOR_ID,
        vendor_name=VENDOR_NAME,
        invoice_date=fake.date_this_year(),
        currency="USD",
        line_items=[
            LineItem(description="Bulk sensor order", quantity=10, unit_rate=3900.0, line_total=39000.0),
            LineItem(description="Annual maintenance contract", quantity=5, unit_rate=2900.0, line_total=14500.0),
        ],
        total_amount=39000.0 + 14500.0,
    )
    return invoice.model_dump(mode="json")


def build_scenario_e() -> dict:
    """Structurally malformed via negative numerical values (distinct from
    Scenario C's empty-array/corrupted-string failure modes).

    Built as a raw dict, bypassing the Invoice model, since this must also
    fail Agent 1's extraction step.
    """
    return {
        "invoice_id": "INV-E-0001",
        "vendor_id": VENDOR_ID,
        "vendor_name": VENDOR_NAME,
        "invoice_date": str(fake.date_this_year()),
        "currency": "USD",
        "line_items": [
            {"description": "Industrial sensors (batch)", "quantity": -3, "unit_rate": 1200.0, "line_total": -3600.0},
        ],
        "total_amount": -3600.0,
    }


def main() -> None:
    scenarios = {
        "A (compliant)": build_scenario_a(),
        "B (anomalous rate)": build_scenario_b(),
        "C (malformed - empty items + corrupted string)": build_scenario_c(),
        "D (anomalous total cap)": build_scenario_d(),
        "E (malformed - negative values)": build_scenario_e(),
    }
    for label, payload in scenarios.items():
        path = _write(payload["invoice_id"], payload)
        print(f"Scenario {label}: wrote {path}")


if __name__ == "__main__":
    main()
