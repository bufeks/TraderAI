import pandas as pd

from traderai.risk import concentration, herfindahl, max_drawdown


def test_herfindahl_equal_weights():
    # 4 等分なら HHI = 4 * (0.25^2) = 0.25
    assert abs(herfindahl([25, 25, 25, 25]) - 0.25) < 1e-9


def test_herfindahl_single_holding():
    assert herfindahl([100]) == 1.0


def test_herfindahl_empty_or_zero():
    assert herfindahl([]) == 0.0
    assert herfindahl([0, 0]) == 0.0


def test_concentration_metrics():
    con = concentration({"A": 50, "B": 30, "C": 20})
    assert con.top_name == "A"
    assert abs(con.top_weight - 50.0) < 1e-9
    # 実効銘柄数 = 1/HHI
    assert abs(con.effective_n - 1 / con.hhi) < 1e-9
    # 構成比は降順
    assert list(con.weights.keys()) == ["A", "B", "C"]


def test_max_drawdown():
    # 100 → 120 → 60 → 90 : ピーク120から60で -50%
    series = pd.Series([100, 120, 60, 90])
    assert abs(max_drawdown(series) - (-50.0)) < 1e-9


def test_max_drawdown_monotonic_up_is_zero():
    series = pd.Series([100, 110, 120, 130])
    assert max_drawdown(series) == 0.0
