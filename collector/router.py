from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger("fluxwatch.router")


class Router:
    def __init__(self, es_url: str = "http://localhost:9200") -> None:
        self._es_url = es_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=10.0)

    async def route_logs(self, logs: list[dict[str, Any]]) -> None:
        if not logs:
            return
        try:
            import time

            index = f"fluxwatch-logs-{time.strftime('%Y.%m.%d')}"
            body = ""
            for log in logs:
                body += (
                    f'{{"index":{{}}}}\n{__import__("json").dumps(log, default=str)}\n'
                )
            resp = await self._client.post(
                f"{self._es_url}/{index}/_bulk",
                content=body,
                headers={"Content-Type": "application/x-ndjson"},
            )
            if resp.status_code >= 400:
                logger.warning("es_bulk_failed status=%d", resp.status_code)
        except Exception as e:
            logger.warning("es_route_error: %s", e)

    async def route_metrics(self, metrics: list[dict[str, Any]]) -> None:
        if not metrics:
            return
        try:
            import time

            index = f"fluxwatch-metrics-{time.strftime('%Y.%m.%d')}"
            body = ""
            for m in metrics:
                body += (
                    f'{{"index":{{}}}}\n{__import__("json").dumps(m, default=str)}\n'
                )
            resp = await self._client.post(
                f"{self._es_url}/{index}/_bulk",
                content=body,
                headers={"Content-Type": "application/x-ndjson"},
            )
            if resp.status_code >= 400:
                logger.warning("es_metrics_bulk_failed status=%d", resp.status_code)
        except Exception as e:
            logger.warning("metrics_route_error: %s", e)

    async def close(self) -> None:
        await self._client.aclose()
