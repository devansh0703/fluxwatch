from __future__ import annotations

import time
from collections import deque
from typing import Any


class RateOfChangeEvaluator:
    def __init__(self, metric: str = "", window_seconds: float = 300.0, max_rate: float = 3.0) -> None:
        self.metric = metric
        self.window_seconds = window_seconds
        self.max_rate = max_rate
        self._timestamps: deque[float] = deque()

    def evaluate(self, data: dict[str, Any]) -> bool:
        now = time.time()
        self._timestamps.append(now)
        cutoff = now - self.window_seconds
        while self._timestamps and self._timestamps[0] < cutoff:
            self._timestamps.popleft()

        if len(self._timestamps) < 2:
            return False

        rate = len(self._timestamps) / self.window_seconds
        rate_per_min = rate * 60.0
        return rate_per_min > self.max_rate
