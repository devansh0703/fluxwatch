from fluxwatch.metrics import Counter, Histogram, Gauge, Summary, MetricRegistry
from fluxwatch.prometheus import render_metrics


def test_counter_concurrent():
    import threading
    c = Counter("concurrent_counter")
    errors = []

    def worker(n):
        try:
            for _ in range(1000):
                c.inc()
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors
    assert c.get() == 10000.0


def test_histogram_concurrent():
    import threading
    import random
    h = Histogram("concurrent_hist")
    errors = []

    def worker():
        try:
            for _ in range(500):
                h.observe(random.uniform(0, 100))
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors
    assert h.count() == 5000


def test_gauge_thread_safety():
    import threading
    g = Gauge("concurrent_gauge")

    def inc():
        for _ in range(100):
            g.inc()

    def dec():
        for _ in range(100):
            g.dec()

    threads = [threading.Thread(target=inc) for _ in range(5)] + [threading.Thread(target=dec) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert g.get() == 0.0


def test_registry_types():
    reg = MetricRegistry()
    reg.counter("c1", "counter 1")
    reg.gauge("g1", "gauge 1")
    reg.histogram("h1", "histogram 1")
    reg.summary("s1", "summary 1")
    assert len(reg.counters) == 1
    assert len(reg.gauges) == 1
    assert len(reg.histograms) == 1
    assert len(reg.summaries) == 1
    assert reg.counter("c1") is reg.counter("c1")


def test_prometheus_render_full():
    reg = MetricRegistry()
    c = reg.counter("http_requests", labels=["method", "status"])
    h = reg.histogram("request_duration", labels=["endpoint"])
    g = reg.gauge("connections")

    c.inc(100, labels={"method": "GET", "status": "200"})
    c.inc(5, labels={"method": "POST", "status": "500"})
    h.observe(0.1)
    h.observe(0.5)
    g.set(42)

    output = render_metrics(reg)
    lines = output.strip().split("\n")
    assert any("http_requests" in l for l in lines)
    assert any('method="GET"' in l for l in lines)
    assert any("request_duration_bucket" in l for l in lines)
    assert any("connections 42" in l for l in lines)
