from __future__ import annotations

import time
import functools
from typing import Any, Callable, TypeVar

from fluxwatch.context import get_trace_id, get_span_id

F = TypeVar("F", bound=Callable[..., Any])


def latency_decorator(logger: Any, name: str) -> Callable[[F], F]:
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.perf_counter_ns()
            try:
                result = func(*args, **kwargs)
            except Exception:
                elapsed = time.perf_counter_ns() - start
                logger.error(f"{name}_error", latency_ns=elapsed, exc_info=True)
                raise
            elapsed = time.perf_counter_ns() - start
            hist = logger.registry.histogram(f"{name}_latency_ns", description=f"Latency for {name} in nanoseconds")
            hist.observe(float(elapsed))
            logger.info(f"{name}_completed", latency_ns=elapsed)
            return result

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.perf_counter_ns()
            try:
                result = await func(*args, **kwargs)
            except Exception:
                elapsed = time.perf_counter_ns() - start
                logger.error(f"{name}_error", latency_ns=elapsed, exc_info=True)
                raise
            elapsed = time.perf_counter_ns() - start
            hist = logger.registry.histogram(f"{name}_latency_ns", description=f"Latency for {name} in nanoseconds")
            hist.observe(float(elapsed))
            logger.info(f"{name}_completed", latency_ns=elapsed)
            return result

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return wrapper  # type: ignore

    return decorator
