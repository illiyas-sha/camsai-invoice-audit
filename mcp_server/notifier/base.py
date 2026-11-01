"""NotifierPort interface: one method, send(subject, body, level). Backends swap in behind it."""

from __future__ import annotations

from typing import Protocol


class NotifierPort(Protocol):
    async def send(self, level: str, subject: str, body: str) -> dict: ...
