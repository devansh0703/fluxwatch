from __future__ import annotations

import threading
import time
from typing import Any


class Buffer:
    def __init__(self, flush_interval: float = 5.0, max_size: int = 500) -> None:
        self._flush_interval = flush_interval
        self._max_size = max_size
        self._items: list[dict[str, Any]] = []
        self._lock = threading.Lock()
        self._last_flush = time.monotonic()

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._items)

    def add(self, item: dict[str, Any]) -> None:
        with self._lock:
            self._items.append(item)

    def drain(self) -> list[dict[str, Any]]:
        with self._lock:
            items = self._items[:]
            self._items.clear()
            self._last_flush = time.monotonic()
            return items

    def should_flush(self) -> bool:
        with self._lock:
            if len(self._items) >= self._max_size:
                return True
            if time.monotonic() - self._last_flush >= self._flush_interval and self._items:
                return True
            return False

    def flush_if_ready(self) -> list[dict[str, Any]]:
        if self.should_flush():
            return self.drain()
        return []
