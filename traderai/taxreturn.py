"""確定申告の補助(概算)。

⚠️ 確定的な税額計算ではありません。上場株式等の譲渡損益・配当の取り扱いの
一般的な枠組みに基づく概算で、最終判断は税理士・国税庁の手引きで確認のこと。

- 損益通算: 上場株式等の譲渡益・配当と譲渡損は損益通算でき、引ききれない損は
  翌年以降(最長3年)繰越控除できる。
- 外国税額控除: 米国株配当などで源泉徴収された外国税(通常10%)は、日本の
  所得税から外国税額控除として控除できる(限度額計算は本概算では簡略化)。
"""

from __future__ import annotations

from dataclasses import dataclass

GAIN_TAX_RATE = 0.20315  # 上場株式等の譲渡益・配当課税(所得税+住民税+復興)


@dataclass
class OffsetResult:
    gains: float
    dividends: float
    losses: float  # 正の値で渡す(損失額)
    net_taxable: float  # 通算後の課税対象(0 未満なら繰越損)
    tax_before: float  # 通算前に益のみへ課税した場合の税
    tax_after: float  # 通算後の税
    tax_saved: float
    loss_carryforward: float  # 翌年以降へ繰り越す損失


def offset(gains: float, dividends: float, losses: float) -> OffsetResult:
    """譲渡益・配当と譲渡損を損益通算した概算を返す。"""
    income = gains + dividends
    net = income - losses
    net_taxable = max(net, 0.0)
    carry = max(-net, 0.0)
    tax_before = income * GAIN_TAX_RATE
    tax_after = net_taxable * GAIN_TAX_RATE
    return OffsetResult(
        gains=gains,
        dividends=dividends,
        losses=losses,
        net_taxable=net_taxable,
        tax_before=tax_before,
        tax_after=tax_after,
        tax_saved=tax_before - tax_after,
        loss_carryforward=carry,
    )


@dataclass
class ForeignCreditResult:
    foreign_dividends: float
    foreign_tax_paid: float
    domestic_tax_on_dividends: float
    creditable: float  # 控除可能額の概算(限度額=国内税額で頭打ち)
    double_taxed_remainder: float  # 控除しきれない分


def foreign_tax_credit(
    foreign_dividends: float,
    foreign_tax_rate: float = 0.10,
    domestic_rate: float = GAIN_TAX_RATE,
) -> ForeignCreditResult:
    """外国税額控除の概算。

    米国株配当等で源泉徴収された外国税を、国内の配当課税額を限度に控除できる
    ものとして概算する(実際の控除限度額は所得全体に対する按分で決まる)。
    """
    foreign_tax = foreign_dividends * foreign_tax_rate
    domestic_tax = foreign_dividends * domestic_rate
    creditable = min(foreign_tax, domestic_tax)
    return ForeignCreditResult(
        foreign_dividends=foreign_dividends,
        foreign_tax_paid=foreign_tax,
        domestic_tax_on_dividends=domestic_tax,
        creditable=creditable,
        double_taxed_remainder=foreign_tax - creditable,
    )
