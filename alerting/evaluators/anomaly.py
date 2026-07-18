from __future__ import annotations

from collections import deque
from typing import Any


class AnomalyEvaluator:
    def __init__(
        self, metric: str = "", z_threshold: float = 3.0, window_size: int = 100
    ) -> None:
        self.metric = metric
        self.z_threshold = z_threshold
        self.window_size = window_size
        self._values: deque[float] = deque(maxlen=window_size)

    def evaluate(self, data: dict[str, Any]) -> bool:
        value = data.get("value", data.get(self.metric, 0))
        try:
            value = float(value)
        except (TypeError, ValueError):
            return False

        self._values.append(value)

        if len(self._values) < 10:
            return False

        values = list(self._values)
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std = variance**0.5

        if std == 0:
            return False

        z_score = abs(value - mean) / std
        return z_score > self.z_threshold
