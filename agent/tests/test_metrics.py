from fluxwatch.metrics import Counter, Histogram, Gauge, Summary, MetricRegistry


def test_counter_inc_dec():
    c = Counter("requests", labels=["method"])
    c.inc(labels={"method": "GET"})
    c.inc(3, labels={"method": "POST"})
    assert c.get(labels={"method": "GET"}) == 1.0
    assert c.get(labels={"method": "POST"}) == 3.0
    c.dec(1, labels={"method": "POST"})
    assert c.get(labels={"method": "POST"}) == 2.0


def test_counter_no_labels():
    c = Counter("total")
    c.inc()
    c.inc(5)
    assert c.get() == 6.0


def test_gauge_set_inc_dec():
    g = Gauge("connections")
    g.set(10)
    assert g.get() == 10.0
    g.inc(3)
    assert g.get() == 13.0
    g.dec(5)
    assert g.get() == 8.0


def test_histogram_percentiles():
    h = Histogram("latency")
    for i in range(1, 101):
        h.observe(float(i))
    assert h.count() == 100
    assert h.mean() == 50.5
    p50 = h.percentile(50)
    assert 49 <= p50 <= 51
    p99 = h.percentile(99)
    assert p99 >= 98


def test_histogram_labels():
    h = Histogram("latency", labels=["endpoint"])
    h.observe(100, labels={"endpoint": "/api/v1"})
    h.observe(200, labels={"endpoint": "/api/v1"})
    assert h.count(labels={"endpoint": "/api/v1"}) == 2
    assert h.mean(labels={"endpoint": "/api/v1"}) == 150.0
    assert h.count(labels={"endpoint": "/other"}) == 0


def test_histogram_bucket_counts():
    h = Histogram("size", buckets=(10, 100, 1000))
    for v in [5, 50, 500, 5000]:
        h.observe(float(v))
    buckets = h.bucket_counts()
    # Buckets are cumulative (value <= bound)
    assert buckets[10] == 1
    assert buckets[100] == 2
    assert buckets[1000] == 3


def test_summary():
    s = Summary("duration")
    s.observe(10)
    s.observe(20)
    s.observe(30)
    assert s.count() == 3
    assert s.total() == 60.0
    assert s.min_val() == 10.0
    assert s.max_val() == 30.0


def test_summary_empty():
    s = Summary("empty")
    assert s.count() == 0
    assert s.total() == 0.0


def test_metric_registry():
    reg = MetricRegistry()
    c = reg.counter("req_total", "Total requests")
    h = reg.histogram("req_latency", "Request latency")
    g = reg.gauge("connections", "Active connections")
    s = reg.summary("response_size", "Response size")

    c.inc()
    h.observe(0.5)
    g.set(42)
    s.observe(1024)

    assert "req_total" in reg.counters
    assert "req_latency" in reg.histograms
    assert "connections" in reg.gauges
    assert "response_size" in reg.summaries

    c2 = reg.counter("req_total")
    assert c2 is c
