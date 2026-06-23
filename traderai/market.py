"""市場データ取得層。

yfinance をバックエンドに、日本株(例: ``7203.T``)・米国株(例: ``AAPL``)・
暗号資産(例: ``BTC-USD``)・ETF を統一的に扱う。ネットワークや yfinance が
利用できない場合は MarketDataError を送出する(エージェント側で握りつぶさない)。
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


class MarketDataError(RuntimeError):
    """市場データ取得に失敗した場合に送出。"""


@dataclass
class Quote:
    symbol: str
    price: float
    currency: str
    name: str | None = None
    previous_close: float | None = None

    @property
    def change_pct(self) -> float | None:
        if self.previous_close in (None, 0):
            return None
        return (self.price - self.previous_close) / self.previous_close * 100


def _ticker(symbol: str):
    try:
        import yfinance as yf
    except ImportError as exc:  # pragma: no cover - 環境依存
        raise MarketDataError(
            "yfinance がインストールされていません。`pip install yfinance` を実行してください。"
        ) from exc
    return yf.Ticker(symbol)


def get_quote(symbol: str) -> Quote:
    """現在値(またはそれに近い直近値)を取得する。"""
    symbol = symbol.strip().upper()
    ticker = _ticker(symbol)
    try:
        info = ticker.fast_info
        price = info.get("last_price") or info.get("lastPrice")
        prev = info.get("previous_close") or info.get("previousClose")
        currency = info.get("currency") or "USD"
    except Exception as exc:  # noqa: BLE001 - yfinance は多様な例外を投げる
        raise MarketDataError(f"{symbol} の価格取得に失敗しました: {exc}") from exc

    if price is None:
        # フォールバック: 直近終値
        hist = get_history(symbol, period="5d", interval="1d")
        if hist.empty:
            raise MarketDataError(f"{symbol} の価格が見つかりませんでした。")
        price = float(hist["Close"].iloc[-1])
        prev = float(hist["Close"].iloc[-2]) if len(hist) >= 2 else None

    return Quote(
        symbol=symbol,
        price=float(price),
        currency=str(currency),
        previous_close=float(prev) if prev is not None else None,
    )


def get_history(
    symbol: str, period: str = "6mo", interval: str = "1d"
) -> pd.DataFrame:
    """ヒストリカルな OHLCV を取得する。

    period: 1mo, 3mo, 6mo, 1y, 2y, 5y, max など
    interval: 1d, 1wk, 1mo など
    """
    symbol = symbol.strip().upper()
    ticker = _ticker(symbol)
    try:
        hist = ticker.history(period=period, interval=interval, auto_adjust=True)
    except Exception as exc:  # noqa: BLE001
        raise MarketDataError(f"{symbol} の履歴取得に失敗しました: {exc}") from exc
    if hist is None or hist.empty:
        raise MarketDataError(
            f"{symbol} の履歴データが空でした(シンボル誤り、または市場休場の可能性)。"
        )
    return hist
