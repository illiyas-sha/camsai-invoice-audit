"""API 3 - Policy Check: applies the per-line-item rate threshold (from API2) and the $50k total-billing rule."""

from __future__ import annotations


async def policy_check(
    line_items: list[dict],
    total_amount: float,
    rate_ceiling: float,
    total_billing_cap: float,
) -> dict:
    """Return a compliance verdict: flags any line item above the rate ceiling or a total above the cap."""
    breaches = [item for item in line_items if item["unit_rate"] > rate_ceiling]
    total_breach = total_amount > total_billing_cap

    reasons = [
        f"Line item '{item['description']}' rate {item['unit_rate']} exceeds ceiling {rate_ceiling}"
        for item in breaches
    ]
    if total_breach:
        reasons.append(f"Total amount {total_amount} exceeds billing cap {total_billing_cap}")

    return {
        "is_compliant": not breaches and not total_breach,
        "reasons": reasons,
    }
