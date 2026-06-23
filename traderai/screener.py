"""バリュースコア・スクリーナー。

PER・PBR・配当利回り・ROE・売上成長率の 5 指標を 100 点満点で採点する。
採点ロジックは純粋関数(value_score)としてテスト可能にし、yfinance からの
指標取得(fetch_metrics)は分離する。割安・優良銘柄の相対比較が目的で、
将来の値上がりを保証するものではない。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Metrics:
    per: float | None = None  # 株価収益率(倍)
    pbr: float | None = None  # 株価純資産倍率(倍)
    dividend_yield: float | None = None  # 配当利回り(小数, 例 0.03)
    roe: float | None = None  # 自己資本利益率(小数, 例 0.15)
    revenue_growth: float | None = None  # 売上成長率(小数)


@dataclass
class ScoreResult:
    symbol: str
    total: int
    breakdown: dict[str, int]


def _score_per(per: float | None) -> int:
    if per is None or per <= 0:
        return 0
    for limit, pts in ((10, 25), (15, 20), (20, 13), (25, 6)):
        if per < limit:
            return pts
    return 0


def _score_pbr(pbr: float | None) -> int:
    if pbr is None or pbr <= 0:
        return 0
    for limit, pts in ((1.0, 25), (1.5, 20), (2.0, 13), (3.0, 6)):
        if pbr < limit:
            return pts
    return 0


def _score_dividend(dy: float | None) -> int:
    if dy is None or dy < 0:
        return 0
    for limit, pts in ((0.04, 20), (0.03, 16), (0.02, 11), (0.01, 6)):
        if dy >= limit:
            return pts
    return 0


def _score_roe(roe: float | None) -> int:
    if roe is None:
        return 0
    for limit, pts in ((0.20, 15), (0.15, 12), (0.10, 8), (0.05, 4)):
        if roe >= limit:
            return pts
    return 0


def _score_growth(g: float | None) -> int:
    if g is None:
        return 0
    for limit, pts in ((0.20, 15), (0.10, 12), (0.05, 8), (0.0, 4)):
        if g >= limit:
            return pts
    return 0


def value_score(symbol: str, m: Metrics) -> ScoreResult:
    """5 指標を採点して合計(0〜100)と内訳を返す。"""
    breakdown = {
        "PER": _score_per(m.per),
        "PBR": _score_pbr(m.pbr),
        "配当利回り": _score_dividend(m.dividend_yield),
        "ROE": _score_roe(m.roe),
        "売上成長率": _score_growth(m.revenue_growth),
    }
    return ScoreResult(symbol=symbol.upper(), total=sum(breakdown.values()), breakdown=breakdown)


def fetch_metrics(symbol: str) -> Metrics:
    """yfinance から指標を取得する(ネットワーク必要)。"""
    from .market import MarketDataError, _ticker

    try:
        info = _ticker(symbol).info
    except Exception as exc:  # noqa: BLE001
        raise MarketDataError(f"{symbol} の指標取得に失敗しました: {exc}") from exc
    return Metrics(
        per=info.get("trailingPE"),
        pbr=info.get("priceToBook"),
        dividend_yield=info.get("dividendYield"),
        roe=info.get("returnOnEquity"),
        revenue_growth=info.get("revenueGrowth"),
    )
