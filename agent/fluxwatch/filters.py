from __future__ import annotations

import random
from typing import Any


_LEVEL_ORDER = {
    "trace": 0,
    "debug": 1,
    "info": 2,
    "warning": 3,
    "error": 4,
    "critical": 5,
}


class LevelFilter:
    def __init__(self, min_level: str = "info") -> None:
        self.min_level = _LEVEL_ORDER.get(min_level.lower(), 2)

    def should_emit(self, entry: dict[str, Any]) -> bool:
        level = _LEVEL_ORDER.get(entry.get("level", "info").lower(), 2)
        return level >= self.min_level


class SamplingFilter:
    def __init__(self, rate: float = 1.0) -> None:
        self.rate = max(0.0, min(1.0, rate))

    def should_emit(self, entry: dict[str, Any]) -> bool:
        return random.random() < self.rate


class FieldFilter:
    def __init__(
        self, allow: list[str] | None = None, deny: list[str] | None = None
    ) -> None:
        self.allow = set(allow) if allow else None
        self.deny = set(deny) if deny else set()

    def should_emit(self, entry: dict[str, Any]) -> bool:
        if self.allow is not None:
            return bool(self.allow & set(entry.keys()))
        if self.deny:
            return not bool(self.deny & set(entry.keys()))
        return True
