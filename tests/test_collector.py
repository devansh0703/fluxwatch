import json
import time
import asyncio

from collector.enricher import Enricher
from collector.router import Router
from collector.buffer import Buffer
from collector.health import CollectorHealth


def test_enricher_adds_metadata():
    enricher = Enricher()
    entry = {"message": "test", "level": "info"}
    enriched = enricher.enrich(entry)
    assert "hostname" in enriched
    assert "env" in enriched
    assert enriched["message"] == "test"


def test_enricher_preserves_existing():
    enricher = Enricher()
    entry = {"message": "test", "hostname": "custom-host", "env": "staging"}
    enriched = enricher.enrich(entry)
    assert enriched["hostname"] == "custom-host"
    assert enriched["env"] == "staging"


def test_buffer_add_and_drain():
    buf = Buffer(flush_interval=0.1, max_size=10)
    assert buf.size == 0
    buf.add({"msg": "1"})
    buf.add({"msg": "2"})
    assert buf.size == 2
    items = buf.drain()
    assert len(items) == 2
    assert buf.size == 0


def test_buffer_should_flush():
    buf = Buffer(flush_interval=10.0, max_size=3)
    assert not buf.should_flush()
    buf.add({"msg": "1"})
    buf.add({"msg": "2"})
    buf.add({"msg": "3"})
    assert buf.should_flush()


def test_buffer_flush_if_ready():
    buf = Buffer(flush_interval=0.05, max_size=100)
    buf.add({"msg": "1"})
    result = buf.flush_if_ready()
    assert len(result) == 0
    time.sleep(0.1)
    result = buf.flush_if_ready()
    assert len(result) == 1


def test_buffer_drain_clears():
    buf = Buffer()
    buf.add({"a": 1})
    buf.add({"b": 2})
    buf.drain()
    buf.add({"c": 3})
    items = buf.drain()
    assert len(items) == 1
    assert items[0]["c"] == 3


def test_health_summary():
    health = CollectorHealth()
    health.record_event()
    health.record_event()
    health.record_event(dropped=True)
    summary = health.summary()
    assert summary["events_processed"] == 3
    assert summary["events_dropped"] == 1
    assert "uptime_seconds" in summary


async def test_health_check_redis():
    health = CollectorHealth(redis_url="redis://localhost:6379")
    results = await health.check_all()
    assert "redis" in results
    assert isinstance(results["redis"].healthy, bool)


async def test_health_check_es():
    health = CollectorHealth(es_url="http://localhost:9200")
    results = await health.check_all()
    assert "elasticsearch" in results
