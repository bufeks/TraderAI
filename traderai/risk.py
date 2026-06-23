"""ポートフォリオのリスク分析。

外部の現在値に依存しない純粋な計算(集中度・最大ドローダウン)を中心に提供する。
銘柄間相関はヒストリカル価格が必要なため、別途 price フレームを渡して計算する。
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class Concentration:
    weights: dict[str, float]  # 構成比(%)
    hhi: float  # ハーフィンダール指数(0〜1、1 に近いほど集中)
    effective_n: float  # 実効銘柄数(1/HHI)
    top_name: str | None
    top_weight: float  # 最大構成比(%)


def herfindahl(values: list[float]) -> float:
    """評価額リストから HHI(構成比の二乗和)を返す。"""
    total = sum(values)
    if total <= 0:
        return 0.0
    return sum((v / total) ** 2 for v in values)


def concentration(named_values: dict[str, float]) -> Concentration:
    """名前付き評価額から集中度指標を算出する。"""
    total = sum(named_values.values())
    if total <= 0:
        return Concentration({}, 0.0, 0.0, None, 0.0)
    weights = {k: v / total * 100 for k, v in named_values.items()}
    hhi = herfindahl(list(named_values.values()))
    effective_n = 1 / hhi if hhi > 0 else 0.0
    top_name, top_w = max(weights.items(), key=lambda kv: kv[1])
    return Concentration(
        weights=dict(sorted(weights.items(), key=lambda kv: kv[1], reverse=True)),
        hhi=hhi,
        effective_n=effective_n,
        top_name=top_name,
        top_weight=top_w,
    )


def max_drawdown(prices: pd.Series) -> float:
    """価格系列の最大ドローダウン(%)を返す(負値)。"""
    prices = prices.dropna()
    if len(prices) < 2:
        return 0.0
    running_max = prices.cummax()
    drawdown = (prices - running_max) / running_max
    return float(drawdown.min() * 100)


def correlation_matrix(price_frames: dict[str, pd.Series]) -> pd.DataFrame:
    """複数銘柄の日次リターン相関行列を返す。"""
    returns = {
        symbol: series.pct_change().dropna() for symbol, series in price_frames.items()
    }
    df = pd.DataFrame(returns)
    return df.corr()
