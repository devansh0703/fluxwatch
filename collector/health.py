from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger("fluxwatch.health")


@dataclass
class ComponentHealth:
    name: str
    healthy: bool = True
    last_check: float = field(default_factory=time.time)
    error: str = ""
    latency_ms: float = 0.0


class CollectorHealth:
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        es_url: str = "http://localhost:9200",
    ) -> None:
        self._redis_url = redis_url
        self._es_url = es_url
        self._components: dict[str, ComponentHealth] = {}
        self._client = httpx.AsyncClient(timeout=5.0)
        self._start_time = time.time()
        self._events_processed = 0
        self._events_dropped = 0

    async def check_all(self) -> dict[str, ComponentHealth]:
        await self._check_redis()
        await self._check_elasticsearch()
        return dict(self._components)

    async def _check_redis(self) -> None:
        health = ComponentHealth(name="redis")
        start = time.time()
        try:
            import redis.asyncio as aioredis

            r = aioredis.from_url(self._redis_url, socket_connect_timeout=2)
            await r.ping()
            await r.aclose()
            health.latency_ms = (time.time() - start) * 1000
        except Exception as e:
            health.healthy = False
            health.error = str(e)
        health.last_check = time.time()
        self._components["redis"] = health

    async def _check_elasticsearch(self) -> None:
        health = ComponentHealth(name="elasticsearch")
        start = time.time()
        try:
            resp = await self._client.get(f"{self._es_url}/_cluster/health")
            if resp.status_code == 200:
                health.latency_ms = (time.time() - start) * 1000
            else:
                health.healthy = False
                health.error = f"status={resp.status_code}"
        except Exception as e:
            health.healthy = False
            health.error = str(e)
        health.last_check = time.time()
        self._components["elasticsearch"] = health

    def record_event(self, dropped: bool = False) -> None:
        self._events_processed += 1
        if dropped:
            self._events_dropped += 1

    def summary(self) -> dict[str, Any]:
        return {
            "uptime_seconds": time.time() - self._start_time,
            "events_processed": self._events_processed,
            "events_dropped": self._events_dropped,
            "components": {
                k: {"healthy": v.healthy, "error": v.error, "latency_ms": v.latency_ms}
                for k, v in self._components.items()
            },
        }
