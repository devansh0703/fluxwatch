from __future__ import annotations

import asyncio
import json
import random
import time
from typing import Any

import redis.asyncio as aioredis


class SimulatedExchange:
    def __init__(self, name: str, latency_ms: float = 5.0, reject_rate: float = 0.02) -> None:
        self.name = name
        self._latency_ms = latency_ms
        self._reject_rate = reject_rate
        self._connected = True
        self._ws_lag_ms = 0.0
        self._order_id = 1000000
        self._fills: list[dict[str, Any]] = []

    async def connect(self) -> bool:
        await asyncio.sleep(0.01)
        self._connected = True
        return True

    async def disconnect(self) -> None:
        self._connected = False

    async def submit_order(self, side: str, qty: float, price: float) -> dict[str, Any]:
        await asyncio.sleep(self._latency_ms / 1000.0)

        if random.random() < self._reject_rate:
            return {
                "status": "rejected",
                "order_id": None,
                "reason": random.choice(["INSUFFICIENT_FUNDS", "PRICE_BAND", "LOT_SIZE", "RISK_LIMIT"]),
                "exchange": self.name,
                "latency_ms": self._latency_ms * (1 + random.uniform(0, 0.5)),
            }

        self._order_id += 1
        fill_price = price * (1 + random.uniform(-0.001, 0.001))
        return {
            "status": "filled",
            "order_id": self._order_id,
            "fill_price": round(fill_price, 2),
            "fill_qty": qty,
            "side": side,
            "exchange": self.name,
            "latency_ms": self._latency_ms * (1 + random.uniform(0, 0.3)),
            "fee": round(fill_price * qty * 0.0004, 4),
        }

    async def heartbeat(self) -> float:
        self._ws_lag_ms = self._latency_ms * 0.5 + random.uniform(0, 5)
        return self._ws_lag_ms

    async def simulate_reconnect(self) -> float:
        self._connected = False
        reconnect_time = random.uniform(0.1, 2.0)
        await asyncio.sleep(reconnect_time)
        self._connected = True
        return reconnect_time * 1000
