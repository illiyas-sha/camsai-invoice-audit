"""API 2 - Vector Knowledge: embeds the invoice/vendor context and queries Chroma for the matching historical contract threshold."""

from __future__ import annotations

from mcp_server.vectorstore.chroma_store import query_contract


async def vector_knowledge(vendor_id: str, vendor_name: str) -> dict:
    """Look up the historical contract thresholds for this vendor via semantic similarity search."""
    result = query_contract(vendor_id, vendor_name)
    if result is None:
        raise ValueError(f"No historical contract found for vendor {vendor_id}")
    return result
