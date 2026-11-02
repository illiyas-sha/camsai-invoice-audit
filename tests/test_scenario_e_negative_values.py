"""Scenario E: negative numerical values must fail extraction gracefully, distinct from Scenario C's failure modes."""

from __future__ import annotations


async def test_scenario_e_fails_extraction_on_negative_values(run_invoice):
    result = await run_invoice("INV-E-0001")

    assert result.get("error") is not None
    assert "extraction failed" in result["error"]
    assert "greater than 0" in result["error"]
    assert "invoice" not in result
    assert "ledger_id" not in result
    assert result["notification_sent"] is True
