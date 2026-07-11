from __future__ import annotations

import asyncio
import json
import random
import time
from typing import Any

import redis.asyncio as aioredis

from demo.exchanges import SimulatedExchange

import logging

_logger = logging.getLogger(__name__)


class DemoTrader:
    def __init__(self, redis_url: str = "redis://localhost:6379", stream: str = "fluxwatch:logs") -> None:
        self._redis_url = redis_url
        self._stream = stream
        self._redis: aioredis.Redis | None = None
        self._exchanges = [
            SimulatedExchange("BINANCE_USDT", latency_ms=3.0, reject_rate=0.02),
            SimulatedExchange("NSE_FNO", latency_ms=15.0, reject_rate=0.05),
            SimulatedExchange("CME_ES", latency_ms=8.0, reject_rate=0.01),
        ]
        self._running = False
        self._order_count = 0
        self._fill_count = 0
        self._reject_count = 0
        self._total_latency_ns = 0

    async def start(self) -> None:
        self._redis = aioredis.from_url(self._redis_url, decode_responses=True)
        self._running = True

        for ex in self._exchanges:
            await ex.connect()
            await self._emit("exchange_connected", exchange=ex.name, ws_latency_ms=ex._latency_ms)

        await asyncio.gather(
            self._order_loop(),
            self._heartbeat_loop(),
            self._reconnect_loop(),
        )

    async def stop(self) -> None:
        self._running = False
        if self._redis:
            await self._redis.aclose()

    async def _emit(self, event: str, **kwargs: Any) -> None:
        entry = {
            "timestamp_ns": time.time_ns(),
            "service": "demo_trader",
            "env": "demo",
            "level": kwargs.pop("level", "info"),
            "message": event,
            "trace_id": f"{random.getrandbits(128):032x}",
            "span_id": f"{random.getrandbits(64):016x}",
            "extra": kwargs,
        }
        if self._redis:
            try:
                await self._redis.xadd(
                    self._stream,
                    {"data": json.dumps(entry, default=str)},
                    maxlen=100_000,
                )
            except Exception:
                _logger.warning("Failed to emit event to Redis", exc_info=True)

    async def _emit_metric(self, name: str, value: float, tags: dict[str, str] | None = None) -> None:
        entry = {
            "timestamp_ns": time.time_ns(),
            "service": "demo_trader",
            "env": "demo",
            "metric_name": name,
            "metric_value": value,
            "tags": tags or {},
            "trace_id": f"{random.getrandbits(128):032x}",
        }
        if self._redis:
            try:
                await self._redis.xadd(
                    self._stream,
                    {"data": json.dumps(entry, default=str)},
                    maxlen=100_000,
                )
            except Exception:
                _logger.warning("Failed to emit metric to Redis", exc_info=True)

    async def _order_loop(self) -> None:
        while self._running:
            exchange = random.choice(self._exchanges)
            side = random.choice(["buy", "sell"])
            qty = random.randint(1, 100)
            price = random.uniform(100, 50000)

            start = time.perf_counter_ns()
            result = await exchange.submit_order(side, qty, price)
            latency_ns = time.perf_counter_ns() - start

            self._order_count += 1
            self._total_latency_ns += latency_ns
            avg_latency = self._total_latency_ns // self._order_count

            if result["status"] == "filled":
                self._fill_count += 1
                await self._emit(
                    "order_filled",
                    exchange=exchange.name,
                    order_id=result["order_id"],
                    side=side,
                    qty=qty,
                    price=result["fill_price"],
                    fill_latency_ns=latency_ns,
                    fee=result["fee"],
                    latency_ns=latency_ns,
                )
                await self._emit_metric("order_latency_us", latency_ns / 1000, {"exchange": exchange.name, "side": side})
                await self._emit_metric("fill_count", self._fill_count, {"exchange": exchange.name})
            else:
                self._reject_count += 1
                await self._emit(
                    "order_rejected",
                    exchange=exchange.name,
                    side=side,
                    qty=qty,
                    reason=result["reason"],
                    latency_ns=latency_ns,
                    level="warning",
                )
                await self._emit_metric("reject_count", self._reject_count, {"exchange": exchange.name, "reason": result["reason"]})

            reject_rate = self._reject_count / max(1, self._order_count)
            await self._emit_metric("reject_rate", reject_rate, {"exchange": exchange.name})
            await self._emit_metric("avg_latency_us", avg_latency / 1000, {"exchange": exchange.name})
            await self._emit_metric("total_orders", self._order_count)

            await asyncio.sleep(random.uniform(0.001, 0.05))

    async def _heartbeat_loop(self) -> None:
        while self._running:
            for exchange in self._exchanges:
                if exchange._connected:
                    lag = await exchange.heartbeat()
                    await self._emit_metric("ws_heartbeat_lag_ms", lag, {"exchange": exchange.name})
                    await self._emit_metric("ws_message_rate", random.uniform(500, 2000), {"exchange": exchange.name})
            await asyncio.sleep(5.0)

    async def _reconnect_loop(self) -> None:
        while self._running:
            await asyncio.sleep(random.uniform(30, 120))
            exchange = random.choice(self._exchanges)
            await self._emit("ws_disconnect", exchange=exchange.name, level="warning")
            reconnect_ms = await exchange.simulate_reconnect()
            await self._emit(
                "ws_reconnected",
                exchange=exchange.name,
                reconnect_time_ms=reconnect_ms,
                latency_ns=int(reconnect_ms * 1_000_000),
            )
            await self._emit_metric("ws_reconnect_count", 1, {"exchange": exchange.name})


async def main() -> None:
    import os
    trader = DemoTrader(
        redis_url=os.environ.get("FLUXWATCH_REDIS_URL", "redis://localhost:6379"),
        stream=os.environ.get("FLUXWATCH_REDIS_STREAM", "fluxwatch:logs"),
    )
    try:
        await trader.start()
    except KeyboardInterrupt:
        await trader.stop()


if __name__ == "__main__":
    asyncio.run(main())
