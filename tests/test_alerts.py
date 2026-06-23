from pathlib import Path

import pytest

from traderai.alerts import AlertRule, AlertStore, _triggered, format_hit


def test_triggered_gt_lt():
    assert _triggered(150.0, "gt", 100.0) is True
    assert _triggered(50.0, "gt", 100.0) is False
    assert _triggered(50.0, "lt", 100.0) is True
    assert _triggered(150.0, "lt", 100.0) is False


def test_invalid_metric_rejected():
    with pytest.raises(ValueError):
        AlertRule(symbol="AAPL", metric="bogus", op="gt", threshold=1)


def test_invalid_op_rejected():
    with pytest.raises(ValueError):
        AlertRule(symbol="AAPL", metric="price", op="equals", threshold=1)


def test_store_persistence(tmp_path: Path):
    path = tmp_path / "alerts.json"
    store = AlertStore(path)
    store.add(AlertRule("9432.T", "price", "gt", 150.49, note="NTT 取得単価回復"))
    reloaded = AlertStore(path)
    assert len(reloaded.rules) == 1
    assert reloaded.rules[0].symbol == "9432.T"


def test_format_hit():
    rule = AlertRule("NVDA", "rsi", "gt", 70, note="過熱")
    from traderai.alerts import AlertHit

    text = format_hit(AlertHit(rule=rule, observed=75.0))
    assert "NVDA" in text
    assert "rsi" in text
    assert "過熱" in text
