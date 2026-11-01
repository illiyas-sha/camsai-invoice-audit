"""API 5 - Notification/Alert: sends a success, escalation, or error notification via the configured notifier backend."""

from __future__ import annotations

import os

from mcp_server.notifier.base import NotifierPort
from mcp_server.notifier.console_notifier import ConsoleNotifier


def _get_notifier() -> NotifierPort:
    backend = os.getenv("NOTIFIER_BACKEND", "console")
    if backend == "console":
        return ConsoleNotifier()
    raise ValueError(f"Unknown NOTIFIER_BACKEND: {backend!r}")


async def notify(level: str, subject: str, body: str) -> dict:
    """Send a notification. level is one of: success, escalation, error."""
    notifier = _get_notifier()
    return await notifier.send(level=level, subject=subject, body=body)
