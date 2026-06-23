"""テクニカル指標の計算。

外部の TA ライブラリに依存せず、pandas/numpy のみで実装する。
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import pandas as pd


@dataclass
class TechnicalSnapshot:
    symbol: str
    last_close: float
    sma_20: float | None
    sma_50: float | None
    sma_200: float | None
    rsi_14: float | None
    macd: float | None
    macd_signal: float | None
    volatility_annual_pct: float | None

    def to_dict(self) -> dict:
        return asdict(self)


def sma(series: pd.Series, window: int) -> float | None:
    if len(series) < window:
        return None
    return float(series.rolling(window).mean().iloc[-1])


def rsi(series: pd.Series, period: int = 14) -> float | None:
    if len(series) < period + 1:
        return None
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = float(gain.rolling(period).mean().iloc[-1])
    avg_loss = float(loss.rolling(period).mean().iloc[-1])
    if pd.isna(avg_gain) or pd.isna(avg_loss):
        return None
    if avg_loss == 0:
        # 下落が無ければ RSI は 100(上昇のみ)。上昇も無ければ中立の 50。
        return 100.0 if avg_gain > 0 else 50.0
    rs = avg_gain / avg_loss
    return float(100 - (100 / (1 + rs)))


def macd(
    series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
) -> tuple[float | None, float | None]:
    if len(series) < slow + signal:
        return None, None
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return float(macd_line.iloc[-1]), float(signal_line.iloc[-1])


def annualized_volatility(series: pd.Series) -> float | None:
    """日次リターンから年率換算ボラティリティ(%)を算出。"""
    if len(series) < 2:
        return None
    returns = series.pct_change().dropna()
    if returns.empty:
        return None
    daily_std = float(returns.std())
    return daily_std * (252 ** 0.5) * 100


def analyze(symbol: str, history: pd.DataFrame) -> TechnicalSnapshot:
    """OHLCV 履歴からテクニカルスナップショットを生成する。"""
    close = history["Close"].dropna()
    macd_line, signal_line = macd(close)
    return TechnicalSnapshot(
        symbol=symbol.upper(),
        last_close=float(close.iloc[-1]),
        sma_20=sma(close, 20),
        sma_50=sma(close, 50),
        sma_200=sma(close, 200),
        rsi_14=rsi(close),
        macd=macd_line,
        macd_signal=signal_line,
        volatility_annual_pct=annualized_volatility(close),
    )
