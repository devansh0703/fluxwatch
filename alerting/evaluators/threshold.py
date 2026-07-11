from __future__ import annotations

from typing import Any


class ThresholdEvaluator:
    def __init__(self, metric: str = "", op: str = ">", threshold: float = 0.0) -> None:
        self.metric = metric
        self.op = op
        self.threshold = threshold

    def evaluate(self, data: dict[str, Any]) -> bool:
        value = data.get("value", data.get(self.metric, 0))
        try:
            value = float(value)
        except (TypeError, ValueError):
            return False

        if self.op == ">":
            return value > self.threshold
        elif self.op == ">=":
            return value >= self.threshold
        elif self.op == "<":
            return value < self.threshold
        elif self.op == "<=":
            return value <= self.threshold
        elif self.op == "==":
            return value == self.threshold
        elif self.op == "!=":
            return value != self.threshold
        return False
