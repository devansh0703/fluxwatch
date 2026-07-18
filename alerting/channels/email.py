from __future__ import annotations

import json
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

logger = logging.getLogger("fluxwatch.alerting.email")


class EmailChannel:
    def __init__(
        self,
        smtp_host: str = "localhost",
        smtp_port: int = 25,
        from_addr: str = "fluxwatch@localhost",
        to_addrs: list[str] | None = None,
        username: str = "",
        password: str = "",
        use_tls: bool = False,
    ) -> None:
        self._smtp_host = smtp_host
        self._smtp_port = smtp_port
        self._from_addr = from_addr
        self._to_addrs = to_addrs or []
        self._username = username
        self._password = password
        self._use_tls = use_tls

    async def send(self, alert: dict[str, Any]) -> None:
        if not self._to_addrs:
            logger.warning("email_no_recipients")
            return

        severity = alert.get("severity", "unknown")
        rule = alert.get("rule", "unknown")
        resolved = alert.get("resolved", False)
        status = "RESOLVED" if resolved else "FIRING"

        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"[FluxWatch {status}] [{severity.upper()}] {rule}"
        msg["From"] = self._from_addr
        msg["To"] = ", ".join(self._to_addrs)

        html = f"""
        <html>
        <body style="font-family: monospace; background: #1a1a2e; color: #e0e0e0; padding: 20px;">
            <h2 style="color: {"#36a64f" if resolved else "#ff4444"};">[{status}] {rule}</h2>
            <p><strong>Severity:</strong> {severity}</p>
            <p><strong>Message:</strong> {alert.get("message", "")}</p>
            <p><strong>Timestamp:</strong> {alert.get("timestamp", "")}</p>
            <h3>Data</h3>
            <pre style="background: #0f0f23; padding: 10px; border-radius: 4px;">{json.dumps(alert.get("data", {}), indent=2)}</pre>
        </body>
        </html>
        """
        msg.attach(MIMEText(html, "html"))

        import asyncio

        await asyncio.get_event_loop().run_in_executor(None, self._send_sync, msg)

    def _send_sync(self, msg: MIMEMultipart) -> None:
        try:
            with smtplib.SMTP(self._smtp_host, self._smtp_port) as server:
                if self._use_tls:
                    server.starttls()
                if self._username:
                    server.login(self._username, self._password)
                server.sendmail(self._from_addr, self._to_addrs, msg.as_string())
        except Exception as e:
            logger.error("email_send_error: %s", e)
