"""税の概算(資産形成の意思決定支援用)。

⚠️ これは確定的な税額計算ではなく、公開されている税率表に基づく概算です。
実際の税額は各種控除・住民税の自治体差・端数処理等で変わります。最終的な
判断は税理士や公式シミュレータでご確認ください。

- 所得税は超過累進(課税所得に対する限界税率)。
- 住民税は概ね一律 10%(所得割)として扱う。
- iDeCo 掛金は全額が小規模企業共済等掛金控除 → 所得控除になり、
  限界税率(所得税+住民税)分だけ税が軽減される(掛金が税率境界を
  またがない前提の概算)。
"""

from __future__ import annotations

from dataclasses import dataclass

# 所得税の速算表(課税所得の上限, 限界税率)。2025 年時点の区分。
INCOME_TAX_BRACKETS: list[tuple[float, float]] = [
    (1_950_000, 0.05),
    (3_300_000, 0.10),
    (6_950_000, 0.20),
    (9_000_000, 0.23),
    (18_000_000, 0.33),
    (40_000_000, 0.40),
    (float("inf"), 0.45),
]

RESIDENT_TAX_RATE = 0.10  # 住民税(所得割)概算


def marginal_income_tax_rate(taxable_income: float) -> float:
    """課税所得に対する所得税の限界税率を返す。"""
    for threshold, rate in INCOME_TAX_BRACKETS:
        if taxable_income <= threshold:
            return rate
    return 0.45


def combined_marginal_rate(
    taxable_income: float, resident_rate: float = RESIDENT_TAX_RATE
) -> float:
    """所得税+住民税の合算限界税率(概算)。"""
    return marginal_income_tax_rate(taxable_income) + resident_rate


@dataclass
class IdecoTaxBenefit:
    annual_contribution: float
    combined_rate: float
    annual_saving: float
    years: int
    total_saving: float


def ideco_tax_benefit(
    monthly_contribution: float,
    taxable_income: float,
    years: int = 1,
    resident_rate: float = RESIDENT_TAX_RATE,
) -> IdecoTaxBenefit:
    """iDeCo 掛金による年間/累計の節税概算を返す。"""
    annual = monthly_contribution * 12
    rate = combined_marginal_rate(taxable_income, resident_rate)
    annual_saving = annual * rate
    return IdecoTaxBenefit(
        annual_contribution=annual,
        combined_rate=rate,
        annual_saving=annual_saving,
        years=years,
        total_saving=annual_saving * years,
    )


# --- NISA(2024〜の新制度) -------------------------------------------
NISA_TSUMITATE_ANNUAL = 1_200_000  # つみたて投資枠 年間
NISA_GROWTH_ANNUAL = 2_400_000  # 成長投資枠 年間
NISA_ANNUAL_TOTAL = 3_600_000  # 年間合計
NISA_LIFETIME = 18_000_000  # 生涯上限(簿価)

TAXABLE_GAIN_RATE = 0.20315  # 課税口座での譲渡益・配当課税(所得税+住民税+復興)


def nisa_remaining(growth_used: float, tsumitate_used: float) -> dict[str, float]:
    """NISA 年間枠の残額を返す(簡易)。"""
    return {
        "つみたて投資枠_残": max(NISA_TSUMITATE_ANNUAL - tsumitate_used, 0),
        "成長投資枠_残": max(NISA_GROWTH_ANNUAL - growth_used, 0),
    }


def taxable_account_tax(gain: float) -> float:
    """課税口座で利益が出た場合の概算税額(NISA なら 0)。"""
    return max(gain, 0) * TAXABLE_GAIN_RATE
