from __future__ import annotations

import time
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from fluxwatch.core import FluxWatchLogger


class FastAPILoggingMiddleware:
    def __init__(self, app: Any, logger: FluxWatchLogger) -> None:
        self.app = app
        self.logger = logger

        from starlette.middleware.base import BaseHTTPMiddleware
        from starlette.requests import Request

        class _LoggingMiddleware(BaseHTTPMiddleware):
            def __init__(self, inner_app: Any, fw_logger: FluxWatchLogger) -> None:
                super().__init__(inner_app)
                self.fw_logger = fw_logger

            async def dispatch(self, request: Request, call_next: Any) -> Any:
                start = time.perf_counter_ns()
                response = await call_next(request)
                latency_ns = time.perf_counter_ns() - start
                self.fw_logger.info(
                    "http_request",
                    method=request.method,
                    path=str(request.url.path),
                    status=response.status_code,
                    latency_ns=latency_ns,
                    remote_addr=request.client.host if request.client else "",
                    user_agent=request.headers.get("user-agent", ""),
                )
                return response

        from starlette.middleware import Middleware

        app.add_middleware(Middleware(_LoggingMiddleware, fw_logger=logger))
