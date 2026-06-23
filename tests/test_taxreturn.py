from traderai.taxreturn import GAIN_TAX_RATE, foreign_tax_credit, offset


def test_offset_with_loss_reduces_tax():
    r = offset(gains=1_000_000, dividends=200_000, losses=400_000)
    assert r.net_taxable == 800_000
    assert abs(r.tax_after - 800_000 * GAIN_TAX_RATE) < 1e-6
    assert r.tax_saved > 0
    assert r.loss_carryforward == 0


def test_offset_net_loss_carryforward():
    r = offset(gains=100_000, dividends=0, losses=500_000)
    assert r.net_taxable == 0
    assert r.loss_carryforward == 400_000
    assert r.tax_after == 0


def test_offset_no_loss():
    r = offset(gains=300_000, dividends=0, losses=0)
    assert r.tax_before == r.tax_after
    assert r.tax_saved == 0


def test_foreign_tax_credit_full():
    # 外国税10% < 国内20.315% → 全額控除可能
    f = foreign_tax_credit(100_000, foreign_tax_rate=0.10)
    assert abs(f.foreign_tax_paid - 10_000) < 1e-6
    assert abs(f.creditable - 10_000) < 1e-6
    assert f.double_taxed_remainder == 0


def test_foreign_tax_credit_capped():
    # 外国税が国内税額を超える場合は国内税額で頭打ち
    f = foreign_tax_credit(100_000, foreign_tax_rate=0.30)
    assert abs(f.creditable - 100_000 * GAIN_TAX_RATE) < 1e-6
    assert f.double_taxed_remainder > 0
