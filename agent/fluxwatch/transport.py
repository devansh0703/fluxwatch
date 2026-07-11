from __future__ import annotations

import json
import logging
import threading
import time
from typing import Any

import redis.asyncio as aioredis

from fluxwatch.config import FluxWatchConfig


class RedisTransport:
    def __init__(self, config: FluxWatchConfig) -> None:
        self._stream = config.redis_stream
        self._max_len = config.redis_max_len
        self._batch_size = config.batch_size
        self._flush_interval = config.flush_interval_ms / 1000.0
        self._buffer: list[str] = []
        self._lock = threading.Lock()
        self._running = True
        self._drop_count = 0
        self._overflow_max = config.buffer_max_size

        self._pool = aioredis.ConnectionPool.from_url(
            config.redis_url, decode_responses=True, max_connections=5
        )
        self._client = aioredis.Redis(connection_pool=self._pool)
        self._flusher = threading.Thread(target=self._flush_loop, daemon=True)
        self._flusher.start()

    def send(self, rendered: str, entry: dict[str, Any] | None = None) -> None:
        with self._lock:
            if len(self._buffer) >= self._overflow_max:
                self._buffer.pop(0)
                self._drop_count += 1
            self._buffer.append(rendered)
            if len(self._buffer) >= self._batch_size:
                self._flush_locked()

    def flush(self) -> None:
        with self._lock:
            self._flush_locked()

    def _flush_locked(self) -> None:
        if not self._buffer:
            return
        batch = self._buffer[:]
        self._buffer.clear()
        try:
            pipe = self._client.pipeline(transaction=False)
            for item in batch:
                pipe.xadd(self._stream, {"data": item}, maxlen=self._max_len)
            pipe.execute(disable_decoding=True)
        except Exception as e:
            logging.getLogger("fluxwatch.transport").warning("flush_failed: %s", e)

    def _flush_loop(self) -> None:
        while self._running:
            time.sleep(self._flush_interval)
            self.flush()

    def close(self) -> None:
        self._running = False
        if self._flusher.is_alive():
            self._flusher.join(timeout=2.0)
        self.flush()
        try:
            self._client.aclose()
        except Exception:
            logging.getLogger("fluxwatch.transport").warning("Failed to close Redis client", exc_info=True)


class _NoopTransport:
    def __init__(self, max_size: int = 10_000) -> None:
        self._buffer: list[str] = []
        self._overflow_max = max_size

    def send(self, rendered: str, entry: dict[str, Any] | None = None) -> None:
        if len(self._buffer) >= self._overflow_max:
            self._buffer.pop(0)
        self._buffer.append(rendered)

    def flush(self) -> None:
        pass

    def close(self) -> None:
        pass
