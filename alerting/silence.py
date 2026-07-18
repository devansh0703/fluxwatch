from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class Silence:
    rule_name: str
    start_time: float
    end_time: float
    comment: str = ""


class SilenceManager:
    def __init__(self) -> None:
        self._silences: list[Silence] = []

    def add_silence(
        self, rule_name: str, duration_seconds: float, comment: str = ""
    ) -> Silence:
        now = time.time()
        silence = Silence(
            rule_name=rule_name,
            start_time=now,
            end_time=now + duration_seconds,
            comment=comment,
        )
        self._silences.append(silence)
        return silence

    def remove_silence(self, silence: Silence) -> None:
        self._silences = [s for s in self._silences if s is not silence]

    def is_silenced(self, rule_name: str) -> bool:
        now = time.time()
        self._silences = [s for s in self._silences if s.end_time > now]
        return any(s.rule_name == rule_name for s in self._silences)

    def active_silences(self) -> list[Silence]:
        now = time.time()
        self._silences = [s for s in self._silences if s.end_time > now]
        return list(self._silences)

    def enter_maintenance(
        self, duration_seconds: float, comment: str = "maintenance"
    ) -> list[Silence]:
        """Silence ALL rules for a duration."""
        now = time.time()
        silence = Silence(
            rule_name="*",
            start_time=now,
            end_time=now + duration_seconds,
            comment=comment,
        )
        self._silences.append(silence)
        return [silence]

    def is_silenced(self, rule_name: str) -> bool:  # noqa: F811
        now = time.time()
        self._silences = [s for s in self._silences if s.end_time > now]
        return any(s.rule_name in (rule_name, "*") for s in self._silences)
