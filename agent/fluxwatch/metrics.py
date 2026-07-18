from __future__ import annotations

import threading
from dataclasses import dataclass


class Counter:
    def __init__(
        self, name: str, description: str = "", labels: list[str] | None = None
    ) -> None:
        self.name = name
        self.description = description
        self.labels = labels or []
        self._values: dict[tuple[str, ...], float] = {}
        self._lock = threading.Lock()

    def _key(self, labels: dict[str, str] | None) -> tuple[str, ...]:
        if not labels:
            return ()
        return tuple(labels.get(label, "") for label in self.labels)

    def inc(self, value: float = 1.0, labels: dict[str, str] | None = None) -> None:
        with self._lock:
            key = self._key(labels)
            self._values[key] = self._values.get(key, 0.0) + value

    def dec(self, value: float = 1.0, labels: dict[str, str] | None = None) -> None:
        with self._lock:
            key = self._key(labels)
            self._values[key] = self._values.get(key, 0.0) - value

    def get(self, labels: dict[str, str] | None = None) -> float:
        with self._lock:
            return self._values.get(self._key(labels), 0.0)

    def all_values(self) -> dict[tuple[str, ...], float]:
        with self._lock:
            return dict(self._values)


class Gauge:
    def __init__(
        self, name: str, description: str = "", labels: list[str] | None = None
    ) -> None:
        self.name = name
        self.description = description
        self.labels = labels or []
        self._values: dict[tuple[str, ...], float] = {}
        self._lock = threading.Lock()

    def _key(self, labels: dict[str, str] | None) -> tuple[str, ...]:
        if not labels:
            return ()
        return tuple(labels.get(label, "") for label in self.labels)

    def set(self, value: float, labels: dict[str, str] | None = None) -> None:
        with self._lock:
            self._values[self._key(labels)] = value

    def inc(self, value: float = 1.0, labels: dict[str, str] | None = None) -> None:
        with self._lock:
            key = self._key(labels)
            self._values[key] = self._values.get(key, 0.0) + value

    def dec(self, value: float = 1.0, labels: dict[str, str] | None = None) -> None:
        with self._lock:
            key = self._key(labels)
            self._values[key] = self._values.get(key, 0.0) - value

    def get(self, labels: dict[str, str] | None = None) -> float:
        with self._lock:
            return self._values.get(self._key(labels), 0.0)

    def all_values(self) -> dict[tuple[str, ...], float]:
        with self._lock:
            return dict(self._values)


class Histogram:
    BUCKETS = (0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)

    def __init__(
        self,
        name: str,
        description: str = "",
        labels: list[str] | None = None,
        buckets: tuple[float, ...] | None = None,
    ) -> None:
        self.name = name
        self.description = description
        self.labels = labels or []
        self.buckets = buckets or self.BUCKETS
        self._data: dict[tuple[str, ...], _HistData] = {}
        self._lock = threading.Lock()

    def _key(self, labels: dict[str, str] | None) -> tuple[str, ...]:
        if not labels:
            return ()
        return tuple(labels.get(label, "") for label in self.labels)

    def _get_data(self, key: tuple[str, ...]) -> _HistData:
        if key not in self._data:
            self._data[key] = _HistData(self.buckets)
        return self._data[key]

    def observe(self, value: float, labels: dict[str, str] | None = None) -> None:
        with self._lock:
            key = self._key(labels)
            self._get_data(key).observe(value)

    def percentile(self, p: float, labels: dict[str, str] | None = None) -> float:
        with self._lock:
            key = self._key(labels)
            if key not in self._data:
                return 0.0
            return self._data[key].percentile(p)

    def mean(self, labels: dict[str, str] | None = None) -> float:
        with self._lock:
            key = self._key(labels)
            if key not in self._data:
                return 0.0
            return self._data[key].mean()

    def count(self, labels: dict[str, str] | None = None) -> int:
        with self._lock:
            key = self._key(labels)
            if key not in self._data:
                return 0
            return self._data[key].count

    def bucket_counts(self, labels: dict[str, str] | None = None) -> dict[float, int]:
        with self._lock:
            key = self._key(labels)
            if key not in self._data:
                return {}
            return dict(zip(self._data[key].bounds, self._data[key].buckets))

    def all_data(self) -> dict[tuple[str, ...], _HistData]:
        with self._lock:
            return dict(self._data)


class _HistData:
    __slots__ = ("bounds", "buckets", "count", "sum", "min_val", "max_val", "values")

    def __init__(self, bucket_bounds: tuple[float, ...]) -> None:
        self.bounds = bucket_bounds
        self.buckets = [0] * len(bucket_bounds)
        self.count = 0
        self.sum = 0.0
        self.min_val = float("inf")
        self.max_val = float("-inf")
        self.values: list[float] = []

    def observe(self, value: float) -> None:
        self.count += 1
        self.sum += value
        self.min_val = min(self.min_val, value)
        self.max_val = max(self.max_val, value)
        self.values.append(value)
        for i, bound in enumerate(self.bounds):
            if value <= bound:
                self.buckets[i] += 1

    def percentile(self, p: float) -> float:
        if not self.values:
            return 0.0
        sorted_vals = sorted(self.values)
        idx = int(len(sorted_vals) * p / 100.0)
        idx = min(idx, len(sorted_vals) - 1)
        return sorted_vals[idx]

    def mean(self) -> float:
        return self.sum / self.count if self.count else 0.0


class Summary:
    def __init__(
        self, name: str, description: str = "", labels: list[str] | None = None
    ) -> None:
        self.name = name
        self.description = description
        self.labels = labels or []
        self._data: dict[tuple[str, ...], _SummaryData] = {}
        self._lock = threading.Lock()

    def _key(self, labels: dict[str, str] | None) -> tuple[str, ...]:
        if not labels:
            return ()
        return tuple(labels.get(label, "") for label in self.labels)

    def observe(self, value: float, labels: dict[str, str] | None = None) -> None:
        with self._lock:
            key = self._key(labels)
            if key not in self._data:
                self._data[key] = _SummaryData()
            d = self._data[key]
            d.count += 1
            d.sum += value
            d.min_val = min(d.min_val, value)
            d.max_val = max(d.max_val, value)

    def count(self, labels: dict[str, str] | None = None) -> int:
        with self._lock:
            key = self._key(labels)
            return self._data[key].count if key in self._data else 0

    def total(self, labels: dict[str, str] | None = None) -> float:
        with self._lock:
            key = self._key(labels)
            return self._data[key].sum if key in self._data else 0.0

    def min_val(self, labels: dict[str, str] | None = None) -> float:
        with self._lock:
            key = self._key(labels)
            return self._data[key].min_val if key in self._data else float("inf")

    def max_val(self, labels: dict[str, str] | None = None) -> float:
        with self._lock:
            key = self._key(labels)
            return self._data[key].max_val if key in self._data else float("-inf")


@dataclass
class _SummaryData:
    count: int = 0
    sum: float = 0.0
    min_val: float = float("inf")
    max_val: float = float("-inf")


class MetricRegistry:
    def __init__(self) -> None:
        self._counters: dict[str, Counter] = {}
        self._gauges: dict[str, Gauge] = {}
        self._histograms: dict[str, Histogram] = {}
        self._summaries: dict[str, Summary] = {}
        self._lock = threading.Lock()

    def counter(
        self, name: str, description: str = "", labels: list[str] | None = None
    ) -> Counter:
        with self._lock:
            if name not in self._counters:
                self._counters[name] = Counter(name, description, labels)
            return self._counters[name]

    def gauge(
        self, name: str, description: str = "", labels: list[str] | None = None
    ) -> Gauge:
        with self._lock:
            if name not in self._gauges:
                self._gauges[name] = Gauge(name, description, labels)
            return self._gauges[name]

    def histogram(
        self,
        name: str,
        description: str = "",
        labels: list[str] | None = None,
        buckets: tuple[float, ...] | None = None,
    ) -> Histogram:
        with self._lock:
            if name not in self._histograms:
                self._histograms[name] = Histogram(name, description, labels, buckets)
            return self._histograms[name]

    def summary(
        self, name: str, description: str = "", labels: list[str] | None = None
    ) -> Summary:
        with self._lock:
            if name not in self._summaries:
                self._summaries[name] = Summary(name, description, labels)
            return self._summaries[name]

    @property
    def counters(self) -> dict[str, Counter]:
        return dict(self._counters)

    @property
    def gauges(self) -> dict[str, Gauge]:
        return dict(self._gauges)

    @property
    def histograms(self) -> dict[str, Histogram]:
        return dict(self._histograms)

    @property
    def summaries(self) -> dict[str, Summary]:
        return dict(self._summaries)
