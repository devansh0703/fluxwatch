from __future__ import annotations

import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fluxwatch.metrics import MetricRegistry


class PrometheusExporter:
    def __init__(self, registry: MetricRegistry, port: int = 9100) -> None:
        self._registry = registry
        self._port = port
        self._server: HTTPServer | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        registry = self._registry
        port = self._port

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                if self.path == "/metrics":
                    body = render_metrics(registry)
                    self.send_response(200)
                    self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(body.encode())
                else:
                    self.send_response(404)
                    self.end_headers()

            def log_message(self, format: str, *args: object) -> None:
                import logging as _logging
                _logging.getLogger("fluxwatch.prometheus").debug(format, *args)

        self._server = HTTPServer(("0.0.0.0", port), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._server:
            self._server.shutdown()


def render_metrics(registry: MetricRegistry) -> str:
    lines: list[str] = []

    for name, counter in registry.counters.items():
        lines.append(f"# HELP {name} {counter.description}")
        lines.append(f"# TYPE {name} counter")
        for label_tuple, value in counter.all_values().items():
            labels = _format_labels(label_tuple, counter.labels)
            lines.append(f"{name}{labels} {value}")

    for name, gauge in registry.gauges.items():
        lines.append(f"# HELP {name} {gauge.description}")
        lines.append(f"# TYPE {name} gauge")
        for label_tuple, value in gauge.all_values().items():
            labels = _format_labels(label_tuple, gauge.labels)
            lines.append(f"{name}{labels} {value}")

    for name, hist in registry.histograms.items():
        lines.append(f"# HELP {name} {hist.description}")
        lines.append(f"# TYPE {name} histogram")
        for key, data in hist.all_data().items():
            labels = _format_labels(key, hist.labels)
            cumulative = 0
            for bound, count in zip(data.bounds, data.buckets):
                cumulative += count
                bound_label = _format_labels(key, hist.labels, extra=f"le=\"{bound}\"")
                lines.append(f"{name}_bucket{bound_label} {cumulative}")
            inf_label = _format_labels(key, hist.labels, extra='le="+Inf"')
            lines.append(f"{name}_bucket{inf_label} {data.count}")
            lines.append(f"{name}_sum{labels} {data.sum}")
            lines.append(f"{name}_count{labels} {data.count}")

    for name, summary in registry.summaries.items():
        lines.append(f"# HELP {name} {summary.description}")
        lines.append(f"# TYPE {name} summary")
        # Summary doesn't track per-label data the same way; skip for now

    lines.append("")
    return "\n".join(lines)


def _format_labels(label_tuple: tuple[str, ...], label_names: list[str], extra: str = "") -> str:
    parts = []
    if label_names:
        for name, val in zip(label_names, label_tuple):
            parts.append(f'{name}="{val}"')
    if extra:
        parts.append(extra)
    if parts:
        return "{" + ",".join(parts) + "}"
    return ""
