"""Real/MailHog SMTP notifier, swapped in via env var for the docker phase and the live demo.

Configured entirely through environment variables - no secrets in code or in
git. Never constructed unless NOTIFIER_BACKEND=smtp is explicitly set.
"""

from __future__ import annotations

import asyncio
import os
import smtplib
from email.message import EmailMessage


class SMTPNotifier:
    """Sends a real email via SMTP. Blocking smtplib calls run in a thread so they never stall the event loop."""

    def __init__(self) -> None:
        self.host = os.environ["SMTP_HOST"]
        self.port = int(os.environ.get("SMTP_PORT", "587"))
        self.username = os.environ["SMTP_USERNAME"]
        self.password = os.environ["SMTP_PASSWORD"]
        self.from_addr = os.environ.get("SMTP_FROM", self.username)
        self.to_addr = os.environ["NOTIFICATION_EMAIL_TO"]

    async def send(self, level: str, subject: str, body: str) -> dict:
        await asyncio.to_thread(self._send_sync, level, subject, body)
        return {"sent": True, "backend": "smtp", "to": self.to_addr}

    def _send_sync(self, level: str, subject: str, body: str) -> None:
        message = EmailMessage()
        message["Subject"] = f"[{level.upper()}] {subject}"
        message["From"] = self.from_addr
        message["To"] = self.to_addr
        message.set_content(body)

        with smtplib.SMTP(self.host, self.port, timeout=10) as server:
            server.starttls()
            server.login(self.username, self.password)
            server.send_message(message)
