"""Scenario A: a fully compliant invoice must post to the ledger and send a success notification."""

from __future__ import annotations


async def test_scenario_a_is_compliant_and_posts_to_ledger(run_invoice):
    result = await run_invoice("INV-A-0001")

    assert result.get("error") is None
    assert result["is_compliant"] is True
    assert result["compliance_reasons"] == []
    assert isinstance(result["ledger_id"], int)
    assert result["notification_sent"] is True
