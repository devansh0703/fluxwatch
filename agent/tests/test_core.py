import json
import time

from fluxwatch.core import FluxWatchLogger, configure
from fluxwatch.config import FluxWatchConfig
from fluxwatch.context import new_span, reset_context, get_trace_id, get_span_id
from fluxwatch.formatters import JSONFormatter, LogfmtFormatter, HumanFormatter


def test_logger_emits_structured_json():
    config = FluxWatchConfig(service="test_svc", env="test", min_level="debug")
    logger = FluxWatchLogger(config)
    logger.info("order_submitted", side="buy", qty=100)
    assert len(logger._transport._buffer) == 1
    entry = json.loads(logger._transport._buffer[0])
    assert entry["service"] == "test_svc"
    assert entry["env"] == "test"
    assert entry["level"] == "info"
    assert entry["message"] == "order_submitted"
    assert entry["extra"]["side"] == "buy"
    assert entry["extra"]["qty"] == 100
    assert "timestamp_ns" in entry
    logger.shutdown()


def test_logger_metric_emission():
    config = FluxWatchConfig(service="test_svc", env="test")
    logger = FluxWatchLogger(config)
    logger.metric("order_latency_us", 450, tags={"side": "buy"})
    assert len(logger._transport._buffer) == 1
    entry = json.loads(logger._transport._buffer[0])
    assert entry["metric_name"] == "order_latency_us"
    assert entry["metric_value"] == 450
    assert entry["tags"]["side"] == "buy"
    logger.shutdown()


def test_context_propagation():
    reset_context()
    with new_span("test_span") as span:
        tid = get_trace_id()
        sid = get_span_id()
        assert len(tid) == 32
        assert len(sid) == 16
        assert span.trace_id == tid
    reset_context()


def test_context_trace_continuity():
    reset_context()
    tid1 = get_trace_id()
    with new_span("op1") as span1:
        tid2 = get_trace_id()
        assert tid1 == tid2
        assert span1.trace_id == tid1
    reset_context()


def test_configure_creates_global():
    reset_context()
    logger = configure(service="global_test", redis_url=None)
    assert logger.service == "global_test"
    logger.shutdown()


def test_json_formatter():
    f = JSONFormatter()
    result = f.format(
        {"timestamp_ns": 123, "service": "s", "level": "info", "message": "hi"}
    )
    parsed = json.loads(result)
    assert parsed["service"] == "s"


def test_logfmt_formatter():
    f = LogfmtFormatter()
    result = f.format({"service": "s", "level": "info", "count": 42})
    assert "service=s" in result
    assert "level=info" in result
    assert "count=42" in result


def test_human_formatter():
    f = HumanFormatter()
    result = f.format(
        {
            "timestamp_ns": time.time_ns(),
            "service": "s",
            "level": "info",
            "message": "hello",
        }
    )
    assert "INFO" in result
    assert "hello" in result
    assert "s" in result


def test_level_filter():
    from fluxwatch.filters import LevelFilter

    f = LevelFilter("warning")
    assert f.should_emit({"level": "error"})
    assert f.should_emit({"level": "warning"})
    assert not f.should_emit({"level": "info"})
    assert not f.should_emit({"level": "debug"})


def test_sampling_filter():
    from fluxwatch.filters import SamplingFilter

    f = SamplingFilter(0.0)
    for _ in range(10):
        assert not f.should_emit({"level": "info"})
    f2 = SamplingFilter(1.0)
    for _ in range(10):
        assert f2.should_emit({"level": "info"})
