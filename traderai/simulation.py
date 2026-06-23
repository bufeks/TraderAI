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


def future_value_annual_lump(
    annual_lump: float, annual_return: float, years: int
) -> float:
    """毎年末に annual_lump を投資した場合の将来価値(年複利)。

    iDeCo の節税還付分など、年 1 回入る資金を再投資する想定。
    """
    if annual_return == 0:
        return annual_lump * years
    g = 1 + annual_return
    return annual_lump * ((g**years - 1) / annual_return)


def future_value_with_tax(
    principal: float,
    monthly: float,
    annual_return: float,
    years: int,
    annual_tax_saving: float = 0.0,
) -> float:
    """月次積立 + 年次の節税還付再投資を含む将来価値。"""
    return future_value(principal, monthly, annual_return, years) + (
        future_value_annual_lump(annual_tax_saving, annual_return, years)
    )


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


def future_value_stepup(
    principal: float,
    monthly: float,
    annual_return: float,
    years: int,
    contribution_growth: float = 0.0,
) -> float:
    """毎年 contribution_growth の割合で積立額を増やす場合の将来価値。

    月内は定額・年初に積立額を増額する近似(月次複利)。
    """
    months_per_year = 12
    r = annual_return / 12
    value = principal
    m = monthly
    for _ in range(years):
        for _ in range(months_per_year):
            value = value * (1 + r) + m
        m *= 1 + contribution_growth
    return value


def years_to_target(
    principal: float,
    monthly: float,
    annual_return: float,
    target: float,
    max_years: int = 100,
    contribution_growth: float = 0.0,
) -> float | None:
    """目標額に到達するまでの年数を返す(到達しなければ None)。"""
    if principal >= target:
        return 0.0
    for y in range(1, max_years + 1):
        if future_value_stepup(principal, monthly, annual_return, y, contribution_growth) >= target:
            return y
    return None


def fire_number(annual_expense: float, withdrawal_rate: float = 0.04) -> float:
    """FIRE 必要資産額(年間支出 ÷ 安全引出率)。既定は 4%ルール。"""
    if withdrawal_rate <= 0:
        raise ValueError("withdrawal_rate は正の数を指定してください。")
    return annual_expense / withdrawal_rate
