from __future__ import annotations

import json
import math
import time
from typing import Any


class JSONFormatter:
    def format(self, entry: dict[str, Any]) -> str:
        return json.dumps(entry, default=str, separators=(",", ":"), ensure_ascii=False)


class LogfmtFormatter:
    def format(self, entry: dict[str, Any]) -> str:
        parts = []
        for k, v in entry.items():
            if isinstance(v, dict):
                v = json.dumps(v, default=str, separators=(",", ":"))
            elif isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                v = "NaN"
            elif isinstance(v, str) and (" " in v or "=" in v or '"' in v):
                v = '"' + v.replace("\\", "\\\\").replace('"', '\\"') + '"'
            parts.append(f"{k}={v}")
        return " ".join(parts)


class HumanFormatter:
    _level_colors = {"debug": "\033[36m", "info": "\033[32m", "warning": "\033[33m", "error": "\033[31m", "critical": "\033[1;31m"}
    _reset = "\033[0m"

    def format(self, entry: dict[str, Any]) -> str:
        ts = entry.get("timestamp_ns", 0)
        if ts:
            dt = time.strftime("%H:%M:%S", time.localtime(ts / 1e9))
            ms = f"{(ts % 1_000_000_000) // 1_000_000:03d}"
            ts_str = f"{dt}.{ms}"
        else:
            ts_str = "?"

        level = entry.get("level", "?").upper()
        service = entry.get("service", "?")
        msg = entry.get("message", "")
        trace = entry.get("trace_id", "")[:8]
        latency = entry.get("latency_ns")
        extra = entry.get("extra", {})

        color = self._level_colors.get(level.lower(), "")
        parts = [f"{color}{ts_str} {level:8s}{self._reset} [{service}] {msg}"]
        if trace:
            parts.append(f" trace={trace}")
        if latency is not None:
            parts.append(f" latency={latency / 1e6:.2f}ms")
        for k, v in extra.items():
            parts.append(f" {k}={v}")
        return "".join(parts)
