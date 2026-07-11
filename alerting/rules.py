from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


class Evaluator(Protocol):
    def evaluate(self, data: dict[str, Any]) -> bool: ...


class Channel(Protocol):
    async def send(self, alert: dict[str, Any]) -> None: ...


@dataclass
class Rule:
    name: str
    evaluator: Evaluator
    severity: str = "warning"
    channels: list[Channel] = field(default_factory=list)
    cooldown_seconds: float = 300.0
    message_template: str = "Alert: {rule}"
    query: str = ""
    enabled: bool = True


def load_default_rules() -> list[Rule]:
    from alerting.evaluators.threshold import ThresholdEvaluator
    from alerting.evaluators.anomaly import AnomalyEvaluator
    from alerting.evaluators.rate import RateOfChangeEvaluator
    from alerting.evaluators.absence import AbsenceEvaluator

    rules = [
        Rule(
            name="high_fill_latency",
            evaluator=ThresholdEvaluator(metric="fill_latency_us", op=">", threshold=1000.0),
            severity="critical",
            cooldown_seconds=120.0,
            message_template="Fill latency exceeded 1ms: current value is {value}us",
            query="fill_latency_us",
        ),
        Rule(
            name="high_reject_rate",
            evaluator=ThresholdEvaluator(metric="reject_rate", op=">", threshold=0.05),
            severity="warning",
            cooldown_seconds=300.0,
            message_template="Reject rate exceeded 5%: current rate is {value}",
            query="reject_rate",
        ),
        Rule(
            name="ws_reconnect_rate",
            evaluator=RateOfChangeEvaluator(metric="ws_reconnects", window_seconds=300.0, max_rate=3.0),
            severity="warning",
            cooldown_seconds=600.0,
            message_template="WebSocket reconnect rate too high: {value}/min",
            query="ws_reconnects",
        ),
        Rule(
            name="ws_heartbeat_lag",
            evaluator=ThresholdEvaluator(metric="ws_heartbeat_lag_ms", op=">", threshold=5000.0),
            severity="critical",
            cooldown_seconds=60.0,
            message_template="WS heartbeat lag exceeded 5s: {value}ms",
            query="ws_heartbeat_lag_ms",
        ),
        Rule(
            name="no_data_received",
            evaluator=AbsenceEvaluator(metric="order_events", absence_seconds=60.0),
            severity="critical",
            cooldown_seconds=120.0,
            message_template="No order events received for 60 seconds",
            query="order_events",
        ),
        Rule(
            name="throughput_anomaly",
            evaluator=AnomalyEvaluator(metric="events_per_second", z_threshold=3.0, window_size=100),
            severity="warning",
            cooldown_seconds=300.0,
            message_template="Throughput anomaly detected: {value} events/s (z-score > 3)",
            query="events_per_second",
        ),
    ]
    return rules
