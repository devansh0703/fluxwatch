import json
import time

from fluxwatch.core import FluxWatchLogger, configure
from fluxwatch.config import FluxWatchConfig
from fluxwatch.context import new_span, reset_context, set_trace_context, get_trace_id, get_span_id
from fluxwatch.prometheus import render_metrics


def test_full_logger_lifecycle():
    reset_context()
    config = FluxWatchConfig(service="integration_test", env="test", min_level="debug")
    logger = FluxWatchLogger(config)

    with new_span("test_op"):
        logger.info("test_event", key="value")
        logger.warning("test_warning")
        logger.debug("test_debug")

    assert len(logger._transport._buffer) == 3
    for raw in logger._transport._buffer:
        entry = json.loads(raw)
        assert entry["service"] == "integration_test"
        assert entry["trace_id"] == get_trace_id()
        assert len(entry["trace_id"]) == 32
    logger.shutdown()
    reset_context()


def test_metric_and_prometheus_roundtrip():
    config = FluxWatchConfig(service="metric_test", env="test")
    logger = FluxWatchLogger(config)

    logger.metric("orders_total", 42, tags={"exchange": "binance"})
    logger.metric("orders_total", 10, tags={"exchange": "nse"})

    counter = logger.registry.counter("orders_total", labels=["exchange"])
    counter.inc(labels={"exchange": "binance"})
    counter.inc(5, labels={"exchange": "nse"})

    output = render_metrics(logger.registry)
    assert "orders_total" in output
    assert "binance" in output
    assert "nse" in output
    logger.shutdown()


def test_context_extraction():
    reset_context()
    trace_id = "a" * 32
    span_id = "b" * 16
    set_trace_context(trace_id, span_id)
    assert get_trace_id() == trace_id
    assert get_span_id() == span_id
    reset_context()
    new_id = get_trace_id()
    assert new_id != trace_id


def test_latency_decorator():
    config = FluxWatchConfig(service="latency_test", env="test")
    logger = FluxWatchLogger(config)

    @logger.latency("sync_op")
    def sync_work():
        time.sleep(0.001)
        return 42

    result = sync_work()
    assert result == 42
    assert len(logger._transport._buffer) == 1
    entry = json.loads(logger._transport._buffer[0])
    assert entry["message"] == "sync_op_completed"
    assert entry["latency_ns"] > 0
    logger.shutdown()


def test_latency_decorator_async():
    import asyncio
    config = FluxWatchConfig(service="async_latency_test", env="test")
    logger = FluxWatchLogger(config)

    @logger.latency("async_op")
    async def async_work():
        await asyncio.sleep(0.001)
        return 42

    result = asyncio.get_event_loop().run_until_complete(async_work())
    assert result == 42
    assert len(logger._transport._buffer) == 1
    entry = json.loads(logger._transport._buffer[0])
    assert "async_op_completed" in entry["message"]
    logger.shutdown()
