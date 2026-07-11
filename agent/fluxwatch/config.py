from __future__ import annotations

import os
from dataclasses import dataclass, field

import yaml


@dataclass
class FluxWatchConfig:
    service: str = "unknown"
    env: str = "production"
    redis_url: str | None = None
    redis_stream: str = "fluxwatch:logs"
    redis_max_len: int = 100_000
    batch_size: int = 100
    flush_interval_ms: int = 500
    buffer_max_size: int = 10_000
    min_level: str = "info"
    format: str = "json"
    sample_rate: float | None = None
    field_allowlist: list[str] | None = None
    field_denylist: list[str] | None = None
    prometheus_port: int = 9100
    otel_enabled: bool = False
    hostname: str = ""
    pod_name: str = ""

    @classmethod
    def from_env(cls) -> FluxWatchConfig:
        hostname = os.environ.get("FLUXWATCH_HOSTNAME", os.environ.get("HOSTNAME", ""))
        pod_name = os.environ.get("FLUXWATCH_POD_NAME", "")
        return cls(
            service=os.environ.get("FLUXWATCH_SERVICE", "unknown"),
            env=os.environ.get("FLUXWATCH_ENV", "production"),
            redis_url=os.environ.get("FLUXWATCH_REDIS_URL", "redis://localhost:6379"),
            redis_stream=os.environ.get("FLUXWATCH_REDIS_STREAM", "fluxwatch:logs"),
            redis_max_len=int(os.environ.get("FLUXWATCH_REDIS_MAX_LEN", "100000")),
            batch_size=int(os.environ.get("FLUXWATCH_BATCH_SIZE", "100")),
            flush_interval_ms=int(os.environ.get("FLUXWATCH_FLUSH_INTERVAL_MS", "500")),
            buffer_max_size=int(os.environ.get("FLUXWATCH_BUFFER_MAX_SIZE", "10000")),
            min_level=os.environ.get("FLUXWATCH_MIN_LEVEL", "info"),
            format=os.environ.get("FLUXWATCH_FORMAT", "json"),
            sample_rate=float(os.environ.get("FLUXWATCH_SAMPLE_RATE", "0")) or None,
            field_allowlist=os.environ.get("FLUXWATCH_FIELD_ALLOWLIST", "").split(",") or None,
            field_denylist=os.environ.get("FLUXWATCH_FIELD_DENYLIST", "").split(",") or None,
            prometheus_port=int(os.environ.get("FLUXWATCH_PROMETHEUS_PORT", "9100")),
            otel_enabled=os.environ.get("FLUXWATCH_OTEL_ENABLED", "false").lower() == "true",
            hostname=hostname,
            pod_name=pod_name,
        )

    @classmethod
    def from_yaml(cls, path: str) -> FluxWatchConfig:
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        env_config = cls.from_env()
        merged = {**cls().__dict__, **data}
        for key, val in env_config.__dict__.items():
            env_var = f"FLUXWATCH_{key.upper()}"
            if os.environ.get(env_var):
                merged[key] = val
        return cls(**merged)
