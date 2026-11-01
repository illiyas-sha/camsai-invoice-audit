"""Dev notifier: logs the notification and writes a proof .txt file to outbox/. No SMTP/docker needed."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

OUTBOX_DIR = Path(__file__).resolve().parent.parent.parent / "outbox"

logger = logging.getLogger("notifier.console")


class ConsoleNotifier:
    """Writes each notification to the log and to a timestamped .txt file as proof it fired."""

    async def send(self, level: str, subject: str, body: str) -> dict:
        OUTBOX_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
        path = OUTBOX_DIR / f"{timestamp}_{level}.txt"
        path.write_text(f"Level: {level}\nSubject: {subject}\n\n{body}\n")
        logger.info("[%s] %s -> %s", level.upper(), subject, path)
        return {"sent": True, "backend": "console", "proof_file": str(path)}
