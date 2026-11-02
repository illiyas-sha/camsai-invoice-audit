"""Live Extraction (additive, not one of the required 5 APIs): uses Claude to extract
invoice fields from a real document, returning the same shape fetch_payload returns."""

from __future__ import annotations

from mcp_server.extraction.claude_extractor import extract_invoice


async def extract_live_invoice(content: str, media_type: str) -> dict:
    """Extract a real invoice document (text or image) into a raw invoice dict."""
    return await extract_invoice(content, media_type)
