from __future__ import annotations

import json
import logging
from typing import Any

import httpx

logger = logging.getLogger("fluxwatch.alerting.slack")


class SlackChannel:
    def __init__(
        self, webhook_url: str, channel: str = "#alerts", username: str = "FluxWatch"
    ) -> None:
        self._webhook_url = webhook_url
        self._channel = channel
        self._username = username
        self._client = httpx.AsyncClient(timeout=10.0)

    async def send(self, alert: dict[str, Any]) -> None:
        severity_emoji = {
            "critical": ":rotating_light:",
            "warning": ":warning:",
            "info": ":information_source:",
        }
        emoji = severity_emoji.get(alert.get("severity", ""), ":bell:")

        resolved = alert.get("resolved", False)
        status = "RESOLVED" if resolved else "FIRING"

        payload = {
            "channel": self._channel,
            "username": self._username,
            "icon_emoji": emoji,
            "attachments": [
                {
                    "color": "#ff0000" if not resolved else "#36a64f",
                    "title": f"[{status}] {alert.get('rule', 'unknown')}",
                    "text": alert.get("message", ""),
                    "fields": [
                        {
                            "title": "Severity",
                            "value": alert.get("severity", "unknown"),
                            "short": True,
                        },
                        {
                            "title": "Service",
                            "value": alert.get("data", {}).get("service", "unknown"),
                            "short": True,
                        },
                    ],
                }
            ],
        }

        try:
            resp = await self._client.post(
                self._webhook_url,
                content=json.dumps(payload),
                headers={"Content-Type": "application/json"},
            )
            if resp.status_code != 200:
                logger.warning("slack_send_failed status=%d", resp.status_code)
        except Exception as e:
            logger.error("slack_send_error: %s", e)
