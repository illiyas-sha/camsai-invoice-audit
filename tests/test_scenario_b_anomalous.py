"""Scenario B: a rate-ceiling breach must skip the ledger and escalate instead."""

from __future__ import annotations


async def test_scenario_b_is_anomalous_and_skips_ledger(run_invoice):
    result = await run_invoice("INV-B-0001")

    assert result.get("error") is None
    assert result["is_compliant"] is False
    assert any("exceeds ceiling" in reason for reason in result["compliance_reasons"])
    assert "ledger_id" not in result
    assert result["notification_sent"] is True
