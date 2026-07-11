import asyncio
import time
from unittest.mock import AsyncMock, MagicMock

from alerting.engine import AlertEngine
from alerting.rules import Rule, load_default_rules
from alerting.evaluators.threshold import ThresholdEvaluator
from alerting.evaluators.anomaly import AnomalyEvaluator
from alerting.evaluators.rate import RateOfChangeEvaluator
from alerting.evaluators.absence import AbsenceEvaluator
from alerting.silence import SilenceManager


def test_threshold_evaluator():
    e = ThresholdEvaluator(metric="value", op=">", threshold=10.0)
    assert e.evaluate({"value": 15.0})
    assert not e.evaluate({"value": 5.0})
    assert e.evaluate({"value": 5.0, "other": 15.0}) is False


def test_threshold_operators():
    assert ThresholdEvaluator(op=">=", threshold=10.0).evaluate({"value": 10.0})
    assert ThresholdEvaluator(op="<", threshold=10.0).evaluate({"value": 5.0})
    assert ThresholdEvaluator(op="<=", threshold=10.0).evaluate({"value": 10.0})
    assert ThresholdEvaluator(op="==", threshold=10.0).evaluate({"value": 10.0})
    assert ThresholdEvaluator(op="!=", threshold=10.0).evaluate({"value": 5.0})
    assert not ThresholdEvaluator(op="==", threshold=10.0).evaluate({"value": 5.0})


def test_threshold_bad_value():
    e = ThresholdEvaluator(op=">", threshold=10.0)
    assert not e.evaluate({"value": "not_a_number"})


def test_anomaly_evaluator():
    e = AnomalyEvaluator(metric="value", z_threshold=2.0, window_size=50)
    for _ in range(30):
        assert not e.evaluate({"value": 100.0})
    assert not e.evaluate({"value": 100.0})


def test_anomaly_evaluator_spike():
    e = AnomalyEvaluator(metric="value", z_threshold=2.0, window_size=50)
    for _ in range(30):
        e.evaluate({"value": 100.0})
    result = e.evaluate({"value": 10000.0})
    assert result is True


def test_rate_evaluator():
    e = RateOfChangeEvaluator(metric="count", window_seconds=10.0, max_rate=3.0)
    for _ in range(50):
        e.evaluate({"count": 1})
    assert e.evaluate({"count": 1})


def test_absence_evaluator():
    e = AbsenceEvaluator(metric="events", absence_seconds=1.0)
    e._last_seen = time.time() - 2.0
    assert e.evaluate({"count": 0})
    assert not e.evaluate({"count": 1})


def test_absence_evaluator_no_previous_data():
    e = AbsenceEvaluator(metric="events", absence_seconds=1.0)
    assert not e.evaluate({"count": 0})


def test_silence_manager():
    sm = SilenceManager()
    silence = sm.add_silence("test_rule", duration_seconds=3600)
    assert sm.is_silenced("test_rule")
    assert not sm.is_silenced("other_rule")
    sm.remove_silence(silence)
    assert not sm.is_silenced("test_rule")


def test_maintenance_mode():
    sm = SilenceManager()
    sm.enter_maintenance(duration_seconds=3600, comment="deploying")
    assert sm.is_silenced("any_rule")
    assert sm.is_silenced("another_rule")


def test_engine_fires_alert():
    mock_channel = AsyncMock()
    evaluator = ThresholdEvaluator(metric="value", op=">", threshold=5.0)

    class MockDataSource:
        async def query(self, q):
            return {"value": 10.0}

    rule = Rule(
        name="test_alert",
        evaluator=evaluator,
        severity="critical",
        channels=[mock_channel],
        cooldown_seconds=0,
        message_template="Value is {value}",
    )

    engine = AlertEngine(rules=[rule], data_source=MockDataSource(), eval_interval=1.0)
    asyncio.get_event_loop().run_until_complete(engine._evaluate_all())
    mock_channel.send.assert_called_once()
    alert = mock_channel.send.call_args[0][0]
    assert alert["severity"] == "critical"
    assert alert["rule"] == "test_alert"


def test_engine_cooldown():
    mock_channel = AsyncMock()
    evaluator = ThresholdEvaluator(metric="value", op=">", threshold=5.0)

    class MockDataSource:
        async def query(self, q):
            return {"value": 10.0}

    rule = Rule(
        name="test_cooldown",
        evaluator=evaluator,
        severity="warning",
        channels=[mock_channel],
        cooldown_seconds=3600,
        message_template="Value is {value}",
    )

    engine = AlertEngine(rules=[rule], data_source=MockDataSource(), eval_interval=0)
    asyncio.get_event_loop().run_until_complete(engine._evaluate_all())
    asyncio.get_event_loop().run_until_complete(engine._evaluate_all())
    assert mock_channel.send.call_count == 1


def test_engine_silenced():
    mock_channel = AsyncMock()
    sm = SilenceManager()
    sm.add_silence("silenced_rule", duration_seconds=3600)
    evaluator = ThresholdEvaluator(metric="value", op=">", threshold=5.0)

    class MockDataSource:
        async def query(self, q):
            return {"value": 10.0}

    rule = Rule(
        name="silenced_rule",
        evaluator=evaluator,
        severity="critical",
        channels=[mock_channel],
        cooldown_seconds=0,
    )

    engine = AlertEngine(rules=[rule], silence_manager=sm, data_source=MockDataSource())
    asyncio.get_event_loop().run_until_complete(engine._evaluate_all())
    mock_channel.send.assert_not_called()


def test_load_default_rules():
    rules = load_default_rules()
    assert len(rules) >= 5
    names = {r.name for r in rules}
    assert "high_fill_latency" in names
    assert "high_reject_rate" in names
    assert "ws_reconnect_rate" in names
    assert "ws_heartbeat_lag" in names
    assert "no_data_received" in names
