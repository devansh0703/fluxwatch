from __future__ import annotations

import time
from typing import Any, TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from fluxwatch.core import FluxWatchLogger


class LoggingHTTPTransport(httpx.BaseTransport):
    def __init__(self, logger: FluxWatchLogger, inner: httpx.BaseTransport | None = None) -> None:
        self.logger = logger
        self._inner = inner or httpx.HTTPTransport()

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        start = time.perf_counter_ns()
        response = self._inner.handle_request(request)
        latency_ns = time.perf_counter_ns() - start
        self.logger.info(
            "http_client_request",
            method=request.method,
            url=str(request.url),
            status_code=response.status_code,
            latency_ns=latency_ns,
        )
        return response


class LoggingSession(httpx.Client):
    def __init__(self, logger: FluxWatchLogger, **kwargs: Any) -> None:
        transport = kwargs.pop("transport", None)
        super().__init__(transport=LoggingHTTPTransport(logger, transport), **kwargs)
        self.logger = logger

    def request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        start = time.perf_counter_ns()
        response = super().request(method, url, **kwargs)
        latency_ns = time.perf_counter_ns() - start
        self.logger.info(
            "http_client_request",
            method=method,
            url=url,
            status_code=response.status_code,
            latency_ns=latency_ns,
        )
        return response


def wrap_session(logger: FluxWatchLogger, session: httpx.Client | None = None) -> LoggingSession:
    if session is None:
        return LoggingSession(logger)
    return LoggingSession(logger, transport=session._transport)
