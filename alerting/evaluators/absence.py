from __future__ import annotations

import time
from typing import Any


class AbsenceEvaluator:
    def __init__(self, metric: str = "", absence_seconds: float = 60.0) -> None:
        self.metric = metric
        self.absence_seconds = absence_seconds
        self._last_seen: float = 0.0

    def evaluate(self, data: dict[str, Any]) -> bool:
        count = data.get("count", data.get("value", 0))
        try:
            count = float(count)
        except (TypeError, ValueError):
            count = 0

        if count > 0:
            self._last_seen = time.time()
            return False

        if self._last_seen == 0:
            self._last_seen = time.time()
            return False

        elapsed = time.time() - self._last_seen
        return elapsed > self.absence_seconds

    def reset(self) -> None:
        self._last_seen = time.time()
