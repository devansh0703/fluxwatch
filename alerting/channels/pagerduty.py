from __future__ import annotations

import json
import logging
import time
from typing import Any

import httpx

logger = logging.getLogger("fluxwatch.alerting.pagerduty")


class PagerDutyChannel:
    def __init__(self, routing_key: str) -> None:
        self._routing_key = routing_key
        self._api_url = "https://events.pagerduty.com/v2/enqueue"
        self._client = httpx.AsyncClient(timeout=10.0)

    async def send(self, alert: dict[str, Any]) -> None:
        severity_map = {"critical": "critical", "warning": "warning", "info": "info"}
        severity = severity_map.get(alert.get("severity", ""), "warning")

        payload: dict[str, Any] = {
            "routing_key": self._routing_key,
            "event_action": "resolve" if alert.get("resolved") else "trigger",
            "dedup_key": alert.get("rule", "unknown"),
            "payload": {
                "summary": alert.get("message", "Unknown alert"),
                "source": alert.get("data", {}).get("service", "fluxwatch"),
                "severity": severity,
                "timestamp": time.strftime(
                    "%Y-%m-%dT%H:%M:%SZ",
                    time.gmtime(alert.get("timestamp", time.time())),
                ),
                "custom_details": alert.get("data", {}),
            },
        }

        try:
            resp = await self._client.post(
                self._api_url,
                content=json.dumps(payload),
                headers={"Content-Type": "application/json"},
            )
            if resp.status_code != 202:
                logger.warning("pagerduty_send_failed status=%d", resp.status_code)
        except Exception as e:
            logger.error("pagerduty_send_error: %s", e)
