from __future__ import annotations

import time
import threading
from typing import Any

from fluxwatch.config import FluxWatchConfig
from fluxwatch.context import get_trace_id, get_span_id
from fluxwatch.formatters import JSONFormatter, LogfmtFormatter, HumanFormatter
from fluxwatch.filters import LevelFilter, SamplingFilter, FieldFilter
from fluxwatch.transport import RedisTransport, _NoopTransport
from fluxwatch.metrics import MetricRegistry
from fluxwatch.latency import latency_decorator


class FluxWatchLogger:
    """Structured logger that emits JSON lines to Redis Streams."""

    def __init__(self, config: FluxWatchConfig) -> None:
        self.config = config
        self.service = config.service
        self.env = config.env
        self.registry = MetricRegistry()

        if config.format == "logfmt":
            self._formatter = LogfmtFormatter()
        elif config.format == "human":
            self._formatter = HumanFormatter()
        else:
            self._formatter = JSONFormatter()

        self._filters = []
        if config.min_level:
            self._filters.append(LevelFilter(config.min_level))
        if config.sample_rate and config.sample_rate < 1.0:
            self._filters.append(SamplingFilter(config.sample_rate))
        if config.field_allowlist:
            self._filters.append(FieldFilter(allow=config.field_allowlist))
        if config.field_denylist:
            self._filters.append(FieldFilter(deny=config.field_denylist))

        if config.redis_url:
            self._transport = RedisTransport(config)
        else:
            self._transport = _NoopTransport()

        self._lock = threading.Lock()

    def _emit(self, level: str, event: str, **kwargs: Any) -> None:
        now_ns = time.time_ns()
        extra = kwargs.pop("extra", None) or {}
        extra.update(kwargs)

        log_entry: dict[str, Any] = {
            "timestamp_ns": now_ns,
            "service": self.service,
            "env": self.env,
            "level": level,
            "message": event,
            "trace_id": get_trace_id(),
            "span_id": get_span_id(),
        }

        if "latency_ns" in extra:
            log_entry["latency_ns"] = extra.pop("latency_ns")

        if extra:
            log_entry["extra"] = extra

        for f in self._filters:
            if not f.should_emit(log_entry):
                return

        rendered = self._formatter.format(log_entry)
        self._transport.send(rendered, entry=log_entry)

    def debug(self, event: str, **kwargs: Any) -> None:
        self._emit("debug", event, **kwargs)

    def info(self, event: str, **kwargs: Any) -> None:
        self._emit("info", event, **kwargs)

    def warning(self, event: str, **kwargs: Any) -> None:
        self._emit("warning", event, **kwargs)

    def error(self, event: str, **kwargs: Any) -> None:
        self._emit("error", event, **kwargs)

    def critical(self, event: str, **kwargs: Any) -> None:
        self._emit("critical", event, **kwargs)

    def metric(
        self, name: str, value: float, tags: dict[str, str] | None = None
    ) -> None:
        entry = {
            "timestamp_ns": time.time_ns(),
            "service": self.service,
            "env": self.env,
            "metric_name": name,
            "metric_value": value,
            "tags": tags or {},
            "trace_id": get_trace_id(),
        }
        rendered = self._formatter.format(entry)
        self._transport.send(rendered, entry=entry)

    def latency(self, name: str):
        return latency_decorator(self, name)

    def shutdown(self) -> None:
        self._transport.flush()
        self._transport.close()


_global_logger: FluxWatchLogger | None = None
_lock = threading.Lock()


def configure(
    service: str,
    env: str = "production",
    redis_url: str | None = None,
    min_level: str = "info",
    format: str = "json",
    sample_rate: float | None = None,
    field_allowlist: list[str] | None = None,
    field_denylist: list[str] | None = None,
) -> FluxWatchLogger:
    global _global_logger
    config = FluxWatchConfig(
        service=service,
        env=env,
        redis_url=redis_url,
        min_level=min_level,
        format=format,
        sample_rate=sample_rate,
        field_allowlist=field_allowlist,
        field_denylist=field_denylist,
    )
    with _lock:
        _global_logger = FluxWatchLogger(config)
    return _global_logger


def get_logger() -> FluxWatchLogger | None:
    return _global_logger
