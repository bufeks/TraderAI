import numpy as np
import pandas as pd

from traderai.analysis import analyze, annualized_volatility, rsi, sma


def _frame(prices):
    return pd.DataFrame({"Close": prices})


def test_sma_basic():
    series = pd.Series([1, 2, 3, 4, 5])
    assert sma(series, 5) == 3.0


def test_sma_insufficient_data():
    series = pd.Series([1, 2])
    assert sma(series, 5) is None


def test_rsi_all_gains_is_high():
    series = pd.Series(range(1, 30))  # 単調増加
    value = rsi(series)
    assert value is not None
    assert value > 90  # 上げ続けなら RSI は高い


def test_volatility_nonnegative():
    rng = np.random.default_rng(42)
    prices = pd.Series(100 + rng.standard_normal(300).cumsum())
    vol = annualized_volatility(prices)
    assert vol is not None
    assert vol >= 0


def test_analyze_returns_snapshot():
    prices = list(range(1, 260))  # 約1年分
    snap = analyze("TEST", _frame(prices))
    assert snap.symbol == "TEST"
    assert snap.last_close == 259
    assert snap.sma_20 is not None
    assert snap.sma_200 is not None
