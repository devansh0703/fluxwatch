from __future__ import annotations

import os
import socket
from typing import Any


class Enricher:
    def __init__(self) -> None:
        self._hostname = os.environ.get("FLUXWATCH_HOSTNAME", "")
        if not self._hostname:
            try:
                self._hostname = socket.gethostname()
            except Exception:
                self._hostname = "unknown"
        self._pod_name = os.environ.get("FLUXWATCH_POD_NAME", "")
        self._env = os.environ.get("FLUXWATCH_ENV", "production")
        self._container_id = self._read_container_id()

    def enrich(self, entry: dict[str, Any]) -> dict[str, Any]:
        enriched = dict(entry)
        enriched.setdefault("hostname", self._hostname)
        enriched.setdefault("env", self._env)
        if self._pod_name:
            enriched.setdefault("pod_name", self._pod_name)
        if self._container_id:
            enriched.setdefault("container_id", self._container_id)
        if "timestamp_ns" not in enriched:
            import time
            enriched["timestamp_ns"] = time.time_ns()
        return enriched

    @staticmethod
    def _read_container_id() -> str:
        try:
            with open("/proc/self/cgroup") as f:
                for line in f:
                    if "docker" in line or "kubepods" in line:
                        parts = line.strip().split(":")
                        if len(parts) == 3 and parts[2]:
                            return parts[2][-12:]
        except (FileNotFoundError, PermissionError) as e:
            import logging
            logging.getLogger("fluxwatch.enricher").debug("Could not read container ID: %s", e)
        return ""
