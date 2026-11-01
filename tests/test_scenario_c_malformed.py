"""Scenario C: a malformed payload must fail extraction gracefully, never hang, and still notify."""

from __future__ import annotations


async def test_scenario_c_fails_extraction_without_hanging(run_invoice):
    result = await run_invoice("INV-C-0001")

    assert result.get("error") is not None
    assert "extraction failed" in result["error"]
    assert "invoice" not in result
    assert "ledger_id" not in result
    assert result["notification_sent"] is True
