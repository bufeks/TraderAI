"""ストレステスト。

代表的な相場シナリオ(資産クラス別の下落率)を現在の配分に適用し、
純資産がどれだけ毀損するかを試算する。下落率はあくまで想定値であり、
将来を予測するものではない(意思決定の感応度確認が目的)。
"""

from __future__ import annotations

from dataclasses import dataclass

# シナリオ → 資産クラス別の想定変化率(負=下落)。
SCENARIOS: dict[str, dict[str, float]] = {
    "世界株暴落(リーマン級)": {
        "国内株式": -0.40,
        "米国株式": -0.50,
        "外国株式": -0.45,
        "投資信託": -0.45,
        "暗号資産": -0.70,
    },
    "テック暴落": {
        "米国株式": -0.35,
        "外国株式": -0.20,
        "国内株式": -0.10,
        "投資信託": -0.20,
        "暗号資産": -0.40,
    },
    "トリプル安(株安・債安・円安)": {
        "国内株式": -0.20,
        "米国株式": -0.15,
        "外国株式": -0.18,
        "投資信託": -0.17,
        "暗号資産": -0.25,
    },
    "円高ドル安": {
        "米国株式": -0.15,
        "外国株式": -0.12,
        "投資信託": -0.08,
        "国内株式": -0.05,
    },
    "金利急騰": {
        "国内株式": -0.12,
        "米国株式": -0.18,
        "外国株式": -0.15,
        "投資信託": -0.15,
        "暗号資産": -0.30,
    },
    "暗号資産暴落": {
        "暗号資産": -0.60,
    },
}


@dataclass
class StressResult:
    scenario: str
    before: float
    after: float
    loss: float  # 負値
    loss_pct: float


def apply_scenario(
    values_by_class: dict[str, float], shocks: dict[str, float]
) -> StressResult:
    """資産クラス別評価額にシナリオの変化率を適用した結果を返す。"""
    before = sum(values_by_class.values())
    after = sum(v * (1 + shocks.get(cls, 0.0)) for cls, v in values_by_class.items())
    loss = after - before
    loss_pct = (loss / before * 100) if before else 0.0
    return StressResult(
        scenario="",
        before=before,
        after=after,
        loss=loss,
        loss_pct=loss_pct,
    )


def run_all(values_by_class: dict[str, float]) -> list[StressResult]:
    """全シナリオを適用し、損失の大きい順に返す。"""
    results: list[StressResult] = []
    for name, shocks in SCENARIOS.items():
        r = apply_scenario(values_by_class, shocks)
        r.scenario = name
        results.append(r)
    return sorted(results, key=lambda r: r.loss)
