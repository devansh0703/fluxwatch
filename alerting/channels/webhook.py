from __future__ import annotations

import json
import logging
from typing import Any

import httpx

logger = logging.getLogger("fluxwatch.alerting.webhook")


class WebhookChannel:
    def __init__(self, url: str, headers: dict[str, str] | None = None, method: str = "POST") -> None:
        self._url = url
        self._headers = headers or {"Content-Type": "application/json"}
        self._method = method.upper()
        self._client = httpx.AsyncClient(timeout=10.0)

    async def send(self, alert: dict[str, Any]) -> None:
        payload = {
            "rule": alert.get("rule", ""),
            "severity": alert.get("severity", ""),
            "message": alert.get("message", ""),
            "timestamp": alert.get("timestamp", 0),
            "resolved": alert.get("resolved", False),
            "data": alert.get("data", {}),
        }

        try:
            if self._method == "POST":
                resp = await self._client.post(
                    self._url,
                    content=json.dumps(payload, default=str),
                    headers=self._headers,
                )
            elif self._method == "PUT":
                resp = await self._client.put(
                    self._url,
                    content=json.dumps(payload, default=str),
                    headers=self._headers,
                )
            else:
                logger.warning("webhook_unsupported_method=%s", self._method)
                return

            if resp.status_code >= 400:
                logger.warning("webhook_failed status=%d url=%s", resp.status_code, self._url)
        except Exception as e:
            logger.error("webhook_error url=%s: %s", self._url, e)
