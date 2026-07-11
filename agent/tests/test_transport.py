import json
from fluxwatch.transport import _NoopTransport, RedisTransport
from fluxwatch.config import FluxWatchConfig


def test_noop_transport_buffers():
    t = _NoopTransport()
    t.send('{"msg": "hello"}')
    t.send('{"msg": "world"}')
    assert len(t._buffer) == 2
    assert t._buffer[0] == '{"msg": "hello"}'
    t.flush()
    assert len(t._buffer) == 2
    t.close()


def test_noop_transport_overflow():
    t = _NoopTransport()
    config = FluxWatchConfig(buffer_max_size=5)
    t._overflow_max = config.buffer_max_size
    for i in range(10):
        t.send(f'{{"i": {i}}}')
    assert len(t._buffer) == 5
    assert '"i": 5' in t._buffer[0]


def test_redis_transport_config():
    config = FluxWatchConfig(
        service="test",
        redis_url="redis://localhost:6379",
        batch_size=50,
        flush_interval_ms=1000,
        buffer_max_size=5000,
    )
    assert config.batch_size == 50
    assert config.flush_interval_ms == 1000
    assert config.buffer_max_size == 5000
    assert config.redis_stream == "fluxwatch:logs"
