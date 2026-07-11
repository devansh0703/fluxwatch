from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from alerting.rules import Rule, load_default_rules
from alerting.silence import SilenceManager

logger = logging.getLogger("fluxwatch.alerting")


class AlertEngine:
    def __init__(
        self,
        rules: list[Rule] | None = None,
        silence_manager: SilenceManager | None = None,
        data_source: Any = None,
        eval_interval: float = 30.0,
    ) -> None:
        self._rules = rules or load_default_rules()
        self._silence = silence_manager or SilenceManager()
        self._data_source = data_source
        self._eval_interval = eval_interval
        self._running = False
        self._last_fires: dict[str, float] = {}
        self._active_alerts: dict[str, dict[str, Any]] = {}

    async def start(self) -> None:
        self._running = True
        logger.info("alert_engine_started rules=%d", len(self._rules))
        while self._running:
            await self._evaluate_all()
            await asyncio.sleep(self._eval_interval)

    async def stop(self) -> None:
        self._running = False
        logger.info("alert_engine_stopped")

    async def _evaluate_all(self) -> None:
        for rule in self._rules:
            try:
                await self._evaluate_rule(rule)
            except Exception as e:
                logger.error("rule_eval_failed rule=%s error=%s", rule.name, e)

    async def _evaluate_rule(self, rule: Rule) -> None:
        if self._silence.is_silenced(rule.name):
            return

        now = time.time()
        cooldown_remaining = now - self._last_fires.get(rule.name, 0)
        if cooldown_remaining < rule.cooldown_seconds:
            return

        data = await self._fetch_data(rule)
        if data is None:
            return

        fired = rule.evaluator.evaluate(data)
        if fired:
            self._last_fires[rule.name] = now
            alert = {
                "rule": rule.name,
                "severity": rule.severity,
                "message": rule.message_template.format(**data) if data else rule.message_template,
                "timestamp": now,
                "data": data,
            }
            self._active_alerts[rule.name] = alert
            logger.warning("alert_fired rule=%s severity=%s", rule.name, rule.severity)
            for channel in rule.channels:
                try:
                    await channel.send(alert)
                except Exception as e:
                    logger.error("channel_send_failed channel=%s error=%s", type(channel).__name__, e)
        elif rule.name in self._active_alerts:
            resolved = self._active_alerts.pop(rule.name)
            resolved["resolved"] = True
            resolved["resolved_at"] = time.time()
            logger.info("alert_resolved rule=%s", rule.name)
            for channel in rule.channels:
                try:
                    await channel.send(resolved)
                except Exception as e:
                    logger.error("resolve_send_failed channel=%s error=%s", type(channel).__name__, e)

    async def _fetch_data(self, rule: Rule) -> dict[str, Any] | None:
        if self._data_source is None:
            return {}
        try:
            return await self._data_source.query(rule.query) if hasattr(self._data_source, "query") else {}
        except Exception as e:
            logger.warning("data_fetch_failed rule=%s: %s", rule.name, e)
            return None

    @property
    def active_alerts(self) -> dict[str, dict[str, Any]]:
        return dict(self._active_alerts)
