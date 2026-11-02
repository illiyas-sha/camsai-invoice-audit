"""CLI entrypoint: python -m app.run --scenario a|b|c|d|e runs one invoice through the compiled graph.

Also supports --invoice-file <path> to extract a real document (image or
.txt) via Claude instead of using mock data - see mcp_server/extraction/.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import logging
import mimetypes
import uuid
from pathlib import Path

from agents.mcp_client import MCPToolClient
from orchestrator.graph import build_graph

SCENARIO_TO_INVOICE_ID = {
    "a": "INV-A-0001",
    "b": "INV-B-0001",
    "c": "INV-C-0001",
    "d": "INV-D-0001",
    "e": "INV-E-0001",
}


def _load_document(path: Path) -> tuple[str, str]:
    """Read a real invoice file, returning (content, media_type) for Agent 1's live-extraction path."""
    media_type, _ = mimetypes.guess_type(str(path))
    if media_type and media_type.startswith("image/"):
        return base64.b64encode(path.read_bytes()).decode("ascii"), media_type
    return path.read_text(), "text/plain"


async def run_graph(initial_state: dict) -> dict:
    async with MCPToolClient() as client:
        graph = build_graph(client)
        return await graph.ainvoke(initial_state)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="Run one invoice through the audit orchestrator.")
    parser.add_argument("--scenario", choices=sorted(SCENARIO_TO_INVOICE_ID), help="Run a built-in scenario (a-e).")
    parser.add_argument("--invoice-id", help="Run an arbitrary invoice_id from mock_data/inbox/ instead.")
    parser.add_argument(
        "--invoice-file",
        help="Path to a real invoice document (image or .txt) to extract via Claude instead of using mock data. Requires ANTHROPIC_API_KEY.",
    )
    args = parser.parse_args()

    if not args.scenario and not args.invoice_id and not args.invoice_file:
        parser.error("Pass --scenario a|b|c|d|e, --invoice-id <id>, or --invoice-file <path>")

    trace_id = str(uuid.uuid4())
    if args.invoice_file:
        content, media_type = _load_document(Path(args.invoice_file))
        initial_state = {
            "invoice_id": f"LIVE-{trace_id[:8]}",
            "trace_id": trace_id,
            "document_content": content,
            "document_media_type": media_type,
        }
        label = f"live document {args.invoice_file}"
    else:
        invoice_id = args.invoice_id or SCENARIO_TO_INVOICE_ID[args.scenario]
        initial_state = {"invoice_id": invoice_id, "trace_id": trace_id}
        label = invoice_id

    result = asyncio.run(run_graph(initial_state))

    print(f"\nFinal state for {label}:")
    for key, value in result.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
