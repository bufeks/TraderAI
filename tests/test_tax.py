from traderai.tax import (
    combined_marginal_rate,
    ideco_tax_benefit,
    marginal_income_tax_rate,
    nisa_remaining,
    taxable_account_tax,
)


def test_marginal_brackets():
    assert marginal_income_tax_rate(1_000_000) == 0.05
    assert marginal_income_tax_rate(3_000_000) == 0.10
    assert marginal_income_tax_rate(5_931_000) == 0.20  # 通知書の課税所得
    assert marginal_income_tax_rate(8_000_000) == 0.23
    assert marginal_income_tax_rate(50_000_000) == 0.45


def test_combined_rate():
    assert abs(combined_marginal_rate(5_931_000) - 0.30) < 1e-9


def test_ideco_benefit():
    b = ideco_tax_benefit(23000, 5_931_000, years=21)
    assert b.annual_contribution == 276_000
    # 年間節税 = 276,000 * 0.30
    assert abs(b.annual_saving - 82_800) < 1e-6
    assert abs(b.total_saving - 82_800 * 21) < 1e-6


def test_nisa_remaining():
    rem = nisa_remaining(growth_used=500_000, tsumitate_used=360_000)
    assert rem["成長投資枠_残"] == 2_400_000 - 500_000
    assert rem["つみたて投資枠_残"] == 1_200_000 - 360_000


def test_taxable_account_tax():
    assert abs(taxable_account_tax(1_000_000) - 203_150) < 1
    assert taxable_account_tax(-5000) == 0
