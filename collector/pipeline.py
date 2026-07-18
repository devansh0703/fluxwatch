from __future__ import annotations

import asyncio
import json
import logging

import redis.asyncio as aioredis

from collector.enricher import Enricher
from collector.router import Router
from collector.buffer import Buffer

logger = logging.getLogger("fluxwatch.collector")


class Pipeline:
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        stream: str = "fluxwatch:logs",
        group: str = "collector",
        consumer: str = "collector-1",
        batch_size: int = 100,
        poll_interval: float = 0.1,
        es_url: str = "http://localhost:9200",
    ) -> None:
        self._redis_url = redis_url
        self._stream = stream
        self._group = group
        self._consumer = consumer
        self._batch_size = batch_size
        self._poll_interval = poll_interval
        self._running = False
        self._enricher = Enricher()
        self._router = Router(es_url=es_url)
        self._buffer = Buffer(flush_interval=5.0, max_size=500)
        self._redis: aioredis.Redis | None = None

    async def start(self) -> None:
        self._redis = aioredis.from_url(self._redis_url, decode_responses=True)
        try:
            await self._redis.xgroup_create(
                self._stream, self._group, id="0", mkstream=True
            )
        except aioredis.ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise
        self._running = True
        logger.info("pipeline_started stream=%s group=%s", self._stream, self._group)
        await self._run()

    async def stop(self) -> None:
        self._running = False
        if self._buffer:
            await self._flush_buffer()
        if self._redis:
            await self._redis.aclose()
        logger.info("pipeline_stopped")

    async def _run(self) -> None:
        while self._running:
            try:
                messages = await self._redis.xreadgroup(
                    self._group,
                    self._consumer,
                    {self._stream: ">"},
                    count=self._batch_size,
                    block=int(self._poll_interval * 1000),
                )
                if not messages:
                    continue

                for _stream_name, entries in messages:
                    for msg_id, fields in entries:
                        raw = fields.get("data", "")
                        if not raw:
                            continue
                        try:
                            entry = json.loads(raw)
                        except json.JSONDecodeError:
                            logger.warning("parse_failed msg_id=%s", msg_id)
                            await self._redis.xack(self._stream, self._group, msg_id)
                            continue

                        enriched = self._enricher.enrich(entry)
                        self._buffer.add(enriched)

                        if self._buffer.size >= self._batch_size:
                            await self._flush_buffer()

                        await self._redis.xack(self._stream, self._group, msg_id)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("pipeline_error: %s", e)
                await asyncio.sleep(1.0)

    async def _flush_buffer(self) -> None:
        batch = self._buffer.drain()
        if not batch:
            return
        metrics = [e for e in batch if "metric_name" in e]
        logs = [e for e in batch if "metric_name" not in e]
        if logs:
            await self._router.route_logs(logs)
        if metrics:
            await self._router.route_metrics(metrics)
        logger.debug("flushed logs=%d metrics=%d", len(logs), len(metrics))


async def run_pipeline() -> None:
    import os

    pipeline = Pipeline(
        redis_url=os.environ.get("FLUXWATCH_REDIS_URL", "redis://localhost:6379"),
        stream=os.environ.get("FLUXWATCH_REDIS_STREAM", "fluxwatch:logs"),
        es_url=os.environ.get("FLUXWATCH_ES_URL", "http://localhost:9200"),
    )
    try:
        await pipeline.start()
    except KeyboardInterrupt:
        await pipeline.stop()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_pipeline())


if __name__ == "__main__":
    main()
