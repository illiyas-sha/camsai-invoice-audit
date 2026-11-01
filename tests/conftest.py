"""Shared pytest fixtures: generated scenario payloads, a compiled graph instance, temp sqlite/chroma paths."""

from __future__ import annotations

import uuid

import pytest

from agents.mcp_client import MCPToolClient
from mock_data.generator import main as generate_mock_data
from orchestrator.graph import build_graph


@pytest.fixture(scope="session", autouse=True)
def _generate_fixtures():
    """Regenerate the 3 scenario JSON fixtures once before the test session."""
    generate_mock_data()


@pytest.fixture
def run_invoice():
    """Async helper: await run_invoice(invoice_id) -> final graph state dict.

    Deliberately a plain (non-async, non-yielding) fixture that just returns
    a closure. Each test opens and closes its own MCPToolClient from inside
    its own coroutine - anyio's cancel scopes require setup and teardown to
    happen in the same asyncio Task, which a yield-based async fixture cannot
    guarantee across pytest-asyncio's separate setup/teardown phases.
    """

    async def _run(invoice_id: str) -> dict:
        async with MCPToolClient() as client:
            graph = build_graph(client)
            initial_state = {"invoice_id": invoice_id, "trace_id": str(uuid.uuid4())}
            return await graph.ainvoke(initial_state)

    return _run
