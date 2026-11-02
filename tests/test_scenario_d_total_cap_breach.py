"""Scenario D: every rate is under the ceiling, but the total breaches the $50k billing cap."""

from __future__ import annotations


async def test_scenario_d_breaches_total_cap_not_rate_ceiling(run_invoice):
    result = await run_invoice("INV-D-0001")

    assert result.get("error") is None
    assert result["is_compliant"] is False
    assert any("exceeds billing cap" in reason for reason in result["compliance_reasons"])
    assert not any("exceeds ceiling" in reason for reason in result["compliance_reasons"])
    assert "ledger_id" not in result
    assert result["notification_sent"] is True
