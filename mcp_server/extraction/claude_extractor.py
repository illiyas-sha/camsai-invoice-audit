"""Claude-powered live invoice extraction: turns a real document (image or text) into
the same raw dict shape mock_data/inbox's fetch_payload returns.

Additive to the required, fully-mocked API1 - this needs ANTHROPIC_API_KEY and
a real network call, so it is never used by the automated pytest suite or the
docker-compose `tests` service (both must stay offline per the assessment's
own "no external network dependencies during execution" requirement). It's a
manual/demo-only capability, wired in behind the same Invoice contract Agent 1
already validates against.
"""

from __future__ import annotations

import os

from anthropic import AsyncAnthropic

MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5")

_EXTRACTION_TOOL = {
    "name": "record_invoice",
    "description": "Record the structured fields extracted from the invoice document.",
    "input_schema": {
        "type": "object",
        "properties": {
            "invoice_id": {"type": "string"},
            "vendor_id": {
                "type": "string",
                "description": "A short vendor code. If the document has no explicit code, derive a slug from the vendor name.",
            },
            "vendor_name": {"type": "string"},
            "invoice_date": {"type": "string", "description": "ISO 8601 date, YYYY-MM-DD"},
            "currency": {"type": "string"},
            "line_items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "description": {"type": "string"},
                        "quantity": {"type": "number"},
                        "unit_rate": {"type": "number"},
                        "line_total": {"type": "number"},
                    },
                    "required": ["description", "quantity", "unit_rate", "line_total"],
                },
            },
            "total_amount": {"type": "number"},
        },
        "required": ["invoice_id", "vendor_id", "vendor_name", "invoice_date", "currency", "line_items", "total_amount"],
    },
}

_SYSTEM_PROMPT = (
    "You extract structured data from vendor invoices. Call record_invoice "
    "exactly once with every field you can read from the document. Read "
    "values literally - do not invent plausible-looking numbers for fields "
    "you cannot actually see."
)


async def extract_invoice(content: str, media_type: str) -> dict:
    """Extract invoice fields from a real document via Claude's forced tool-use.

    media_type is "text/plain" (content is the raw invoice text) or an image
    mime type like "image/png" / "image/jpeg" (content is base64-encoded).
    """
    client = AsyncAnthropic()  # reads ANTHROPIC_API_KEY from the environment

    if media_type == "text/plain":
        user_content = [{"type": "text", "text": content}]
    else:
        user_content = [{"type": "image", "source": {"type": "base64", "media_type": media_type, "data": content}}]

    response = await client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=_SYSTEM_PROMPT,
        tools=[_EXTRACTION_TOOL],
        tool_choice={"type": "tool", "name": "record_invoice"},
        messages=[{"role": "user", "content": user_content}],
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == "record_invoice":
            return block.input

    raise ValueError("Claude did not return a record_invoice tool call")
