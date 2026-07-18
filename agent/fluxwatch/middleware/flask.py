from __future__ import annotations

import time
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from fluxwatch.core import FluxWatchLogger


class FlaskLoggingMiddleware:
    def __init__(self, app: Any, logger: FluxWatchLogger) -> None:
        self.app = app
        self.logger = logger

        @app.before_request
        def before_request() -> None:
            from flask import g

            g._fluxwatch_start = time.perf_counter_ns()

        @app.after_request
        def after_request(response: Any) -> Any:
            from flask import g, request

            start = getattr(g, "_fluxwatch_start", None)
            latency_ns = (time.perf_counter_ns() - start) if start else 0
            self.logger.info(
                "http_request",
                method=request.method,
                path=request.path,
                status=response.status_code,
                latency_ns=latency_ns,
                remote_addr=request.remote_addr,
                user_agent=str(request.user_agent),
            )
            return response
