"""Historical vendor contract snippets + their rate thresholds, used to seed the Chroma collection."""

from __future__ import annotations

from mock_data.generator import CONTRACT_RATE_CEILING, TOTAL_BILLING_CAP, VENDOR_ID, VENDOR_NAME

CONTRACTS = [
    {
        "id": f"{VENDOR_ID}-contract-1",
        "document": (
            f"Historical contract for {VENDOR_NAME} ({VENDOR_ID}): standard per-unit "
            f"rate ceiling is ${CONTRACT_RATE_CEILING:,.0f}. Any single line item billed "
            f"above this rate must be escalated for manual review before payment."
        ),
        "metadata": {
            "vendor_id": VENDOR_ID,
            "vendor_name": VENDOR_NAME,
            "rate_ceiling": CONTRACT_RATE_CEILING,
            "total_billing_cap": TOTAL_BILLING_CAP,
        },
    },
]
