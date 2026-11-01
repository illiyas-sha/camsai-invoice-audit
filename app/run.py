"""CLI entrypoint: python -m app.run --scenario a|b|c runs one invoice through the compiled graph."""

from __future__ import annotations

import argparse
import asyncio
import logging
import uuid

from agents.mcp_client import MCPToolClient
from orchestrator.graph import build_graph

SCENARIO_TO_INVOICE_ID = {
    "a": "INV-A-0001",
    "b": "INV-B-0001",
    "c": "INV-C-0001",
}


async def run_invoice(invoice_id: str) -> dict:
    async with MCPToolClient() as client:
        graph = build_graph(client)
        initial_state = {"invoice_id": invoice_id, "trace_id": str(uuid.uuid4())}
        return await graph.ainvoke(initial_state)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="Run one invoice through the audit orchestrator.")
    parser.add_argument("--scenario", choices=sorted(SCENARIO_TO_INVOICE_ID), help="Run a built-in scenario (a/b/c).")
    parser.add_argument("--invoice-id", help="Run an arbitrary invoice_id from mock_data/inbox/ instead.")
    args = parser.parse_args()

    if not args.scenario and not args.invoice_id:
        parser.error("Pass --scenario a|b|c or --invoice-id <id>")

    invoice_id = args.invoice_id or SCENARIO_TO_INVOICE_ID[args.scenario]
    result = asyncio.run(run_invoice(invoice_id))

    print(f"\nFinal state for {invoice_id}:")
    for key, value in result.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
