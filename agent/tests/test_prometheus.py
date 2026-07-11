from fluxwatch.prometheus import render_metrics
from fluxwatch.metrics import MetricRegistry


def test_render_empty():
    reg = MetricRegistry()
    result = render_metrics(reg)
    assert result == ""


def test_render_counter():
    reg = MetricRegistry()
    c = reg.counter("http_requests", "Total HTTP requests", labels=["method"])
    c.inc(labels={"method": "GET"})
    c.inc(5, labels={"method": "POST"})
    output = render_metrics(reg)
    assert "# HELP http_requests Total HTTP requests" in output
    assert "# TYPE http_requests counter" in output
    assert 'method="GET"' in output
    assert 'method="POST"' in output


def test_render_gauge():
    reg = MetricRegistry()
    g = reg.gauge("memory_usage", "Memory usage bytes")
    g.set(1024.0)
    output = render_metrics(reg)
    assert "# TYPE memory_usage gauge" in output
    assert "memory_usage 1024.0" in output


def test_render_histogram():
    reg = MetricRegistry()
    h = reg.histogram("req_duration", "Request duration")
    h.observe(0.1)
    h.observe(0.5)
    output = render_metrics(reg)
    assert "# TYPE req_duration histogram" in output
    assert "req_duration_count" in output
    assert "req_duration_sum" in output
    assert "req_duration_bucket" in output
