# FluxWatch

Trading system observability platform providing structured logging, sub-microsecond latency metrics, and alerting purpose-built for low-latency trading systems. Ships as a drop-in Python agent library, a Redis-backed ingestion pipeline, and a Docker Compose stack with pre-built Grafana dashboards and Kibana saved objects.

## Overview

FluxWatch is a complete observability stack designed for trading infrastructure. It replaces generic logging with structured JSON output that includes trace context, nanosecond timestamps, and metric emission. Data flows from instrumented trading processes through Redis Streams (which survive collector restarts) into Elasticsearch for log exploration and Prometheus for metrics. A custom alerting engine evaluates rules against the collected data and routes notifications to Slack, PagerDuty, email, or generic webhooks.

The platform is deployed as a single `docker compose up` command that brings up Redis, Elasticsearch, Prometheus, Grafana, Kibana, Alertmanager, the collector pipeline, and a simulated trading process that demonstrates the full data flow.

## Architecture

```
Instrumented Trading Processes (FluxWatch Agent)
        |
        v
   Redis Streams (bounded buffer, max-length enforcement)
        |
        +--------------------+
        v                    v
  Elasticsearch          Prometheus
   (structured logs)     (time-series metrics)
        |                    |
        v                    v
     Kibana              Grafana
  (log exploration)     (dashboards)
        |                    |
        +--------+-----------+
                 v
          Alerting Engine
    (threshold, anomaly, rate, absence)
                 |
        +--------+--------+--------+
        v        v        v        v
     Slack  PagerDuty   Email   Webhook
```

## Components

### Agent Library

Drop-in Python logging replacement. Install with `pip install fluxwatch-agent`.

```python
import fluxwatch

log = fluxwatch.configure(service="strategy_alpha")

# Structured logging — every line is JSON with trace context
log.info("order_submitted", side="buy", qty=100, price=42500.50)

# Metric emission — Counter, Histogram, Gauge, Summary
log.metric("order_latency_us", 450, tags={"side": "buy", "symbol": "BTCUSDT"})

# Latency measurement — automatic p50/p95/p99/p999 tracking
@log.latency("fill_handler")
async def handle_fill(fill):
    ...
```

Every log entry includes: `timestamp_ns`, `service`, `env`, `level`, `message`, `trace_id`, `span_id`, `latency_ns`, and arbitrary extra fields. The trace context propagates automatically across async boundaries via `contextvars`.

The agent exposes a zero-config Prometheus `/metrics` endpoint on a configurable port (default 9100). Metric types:

- **Counter**: monotonically increasing (orders sent, fills, rejects)
- **Histogram**: latency distributions with configurable bounds (p50/p95/p99/p999)
- **Gauge**: point-in-time values (queue depth, connection count)
- **Summary**: running statistics (count, sum, min, max)

Middleware adapters are provided for Flask, FastAPI, and outbound HTTP clients (`httpx`).

### Transport

Redis Streams serves as the bounded buffer between agents and the collector. Agents write in batches with configurable batch size and flush interval. Backpressure is handled by enforcing `max-length` on streams — when the buffer fills, the oldest events are dropped and a counter is incremented. The transport is async (`redis[hiredis]`) with a dedicated flush thread.

When Redis is unavailable, the agent falls back to a no-op transport that buffers events in memory (bounded, drops oldest on overflow).

### Collector

The collector reads from Redis Streams, parses JSON, enriches entries with hostname/pod/env metadata, and routes structured logs to Elasticsearch and metrics to Prometheus. It runs as an async event loop with configurable flush intervals.

### Alerting Engine

A custom Python alerting engine that evaluates rules against collected data:

| Rule Type | Logic | Use Case |
|-----------|-------|----------|
| Threshold | Simple comparison (>, <, ==) over a time window | High latency, elevated reject rate |
| Anomaly | Z-score detection against rolling baseline | Fill rate deviation, unusual volume |
| Rate of Change | Compare current rate to historical | Sudden latency increase |
| Absence | No data for N seconds | Service down, WS disconnect |

Alert rules are evaluated on a configurable interval with per-rule cooldowns. Notifications are routed to channels:

| Channel | Protocol |
|---------|----------|
| Slack | Incoming webhook |
| PagerDuty | Events API v2 |
| Email | SMTP |
| Webhook | Generic HTTP POST |

Alert silencing and maintenance windows are supported via the `SilenceManager`.

### Dashboards

Pre-built Grafana dashboards exported as JSON and auto-provisioned on startup:

| Dashboard | Panels |
|-----------|--------|
| Exchange Connectivity | WebSocket reconnect count, connection uptime, message rate, heartbeat lag |
| Order Lifecycle | Orders sent / acknowledged / filled / rejected (funnel), reject rate, fill latency heatmap |
| Latency Analysis | p50/p95/p99/p999 by service, latency distribution histogram, anomaly bands over time |
| Throughput | Events processed/sec by service, queue depth over time, batch flush rate |
| Error Tracking | Error rate by service, top error messages, error rate over time |

Kibana saved objects for log exploration: "All rejects last 1h", "Latency spikes", "Symbol-level breakdown".

### Demo Mode

`docker compose up` includes a simulated trading process (`demo_trader`) that:

- Connects to three simulated exchanges (Binance, NSE, CME) with realistic latencies
- Submits random orders with configurable fill/reject rates
- Emits structured logs and metrics to Redis Streams
- Simulates WebSocket disconnects and reconnections
- Full data flow visible in Grafana and Kibana within 30 seconds

## CLI

```bash
fluxwatch init        # Interactive setup wizard
fluxwatch status      # Check Redis/ES/Prometheus connectivity
fluxwatch test-alert  # Send a test alert through all channels
```

## Getting Started

```bash
docker compose up -d
```

| Service | URL | Credentials |
|---------|-----|-------------|
| Grafana | http://localhost:3000 | admin / fluxwatch |
| Prometheus | http://localhost:9090 | — |
| Kibana | http://localhost:5601 | — |
| Alertmanager | http://localhost:9093 | — |
| Demo trader metrics | http://localhost:9100/metrics | — |

To instrument your own process:

```bash
pip install fluxwatch-agent
```

```python
import fluxwatch

log = fluxwatch.configure(service="my_strategy")
# All subsequent log.info() and log.metric() calls are collected
```

## Tech Stack

| Layer | Technology |
|-------|------------|
| Agent | Python, structlog, contextvars |
| Transport | Redis Streams (redis[hiredis]) |
| Log Storage | Elasticsearch 8.x |
| Metrics Storage | Prometheus TSDB |
| Dashboards | Grafana 10.x (provisioned), Kibana 8.x |
| Alerting | Custom Python engine, Alertmanager |
| Collector | Python async, Redis to ES/Prometheus pipeline |
| Deployment | Docker Compose |

## Configuration

Configuration is loaded from environment variables with optional YAML file override:

| Variable | Default | Description |
|----------|---------|-------------|
| `FLUXWATCH_SERVICE` | `unknown` | Service name for log entries |
| `FLUXWATCH_ENV` | `production` | Environment tag |
| `FLUXWATCH_REDIS_URL` | `redis://localhost:6379` | Redis connection URL |
| `FLUXWATCH_REDIS_STREAM` | `fluxwatch:logs` | Redis Stream name |
| `FLUXWATCH_REDIS_MAX_LEN` | `100000` | Max stream length |
| `FLUXWATCH_BATCH_SIZE` | `100` | Events per batch flush |
| `FLUXWATCH_BUFFER_MAX_SIZE` | `10000` | In-memory buffer size |
| `FLUXWATCH_PROMETHEUS_PORT` | `9100` | Prometheus metrics port |
| `FLUXWATCH_ES_URL` | `http://localhost:9200` | Elasticsearch URL |
| `FLUXWATCH_LOG_LEVEL` | `INFO` | Minimum log level |

## Testing

```bash
pip install -e "agent[dev]" -e ".[dev]"
pytest agent/tests/ tests/ -v
```

Tests cover the agent library (logger output format, metric emission, context propagation, transport), collector (pipeline flow, enrichment), and alerting engine (rule evaluation, channel routing with mocked sends).
