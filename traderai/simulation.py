"""将来資産シミュレーション。

現在の評価額(元本)に対し、毎月の積立を一定の想定年利で運用した場合の
将来価値を月次複利で試算する。投資助言ではなく、前提に基づく単純な試算。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class YearPoint:
    year: int
    contributions: float  # その時点までの累計積立額(元本を除く拠出分)
    value: float  # 評価額(元本 + 積立 + 運用益)

    @property
    def invested(self) -> float:
        """投資元本合計(初期元本 + 累計積立)。value との差が運用益。"""
        return self._principal + self.contributions

    _principal: float = 0.0


def future_value(
    principal: float, monthly: float, annual_return: float, years: int
) -> float:
    """月次複利での将来価値を返す。

    principal: 初期元本
    monthly: 毎月の積立額
    annual_return: 想定年利(例 0.05 = 5%)
    years: 年数
    """
    months = years * 12
    r = annual_return / 12
    if r == 0:
        return principal + monthly * months
    growth = (1 + r) ** months
    fv_principal = principal * growth
    fv_contrib = monthly * ((growth - 1) / r)
    return fv_principal + fv_contrib


def project(
    principal: float, monthly: float, annual_return: float, years: int
) -> list[YearPoint]:
    """年ごとの推移(0 年目=現在から years 年目まで)を返す。"""
    points: list[YearPoint] = []
    for y in range(years + 1):
        value = future_value(principal, monthly, annual_return, y)
        contributions = monthly * 12 * y
        point = YearPoint(year=y, contributions=contributions, value=value)
        point._principal = principal
        points.append(point)
    return points


def scenarios(
    principal: float,
    monthly: float,
    years: int,
    rates: tuple[float, ...] = (0.03, 0.05, 0.07),
) -> dict[float, float]:
    """想定年利ごとの最終評価額を返す(年利 → 最終 value)。"""
    return {rate: future_value(principal, monthly, rate, years) for rate in rates}
