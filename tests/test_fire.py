from traderai.simulation import (
    fire_number,
    future_value,
    future_value_stepup,
    years_to_target,
)


def test_fire_number_4pct():
    assert fire_number(3_000_000, 0.04) == 75_000_000
    assert fire_number(3_000_000, 0.03) == 100_000_000


def test_stepup_equals_flat_when_no_growth():
    flat = future_value(1_000_000, 50_000, 0.05, 10)
    step = future_value_stepup(1_000_000, 50_000, 0.05, 10, contribution_growth=0.0)
    # 月次の畳み込み近似なので厳密一致ではないが十分近い
    assert abs(flat - step) / flat < 0.01


def test_stepup_more_than_flat_with_growth():
    flat = future_value_stepup(1_000_000, 50_000, 0.05, 20, 0.0)
    grown = future_value_stepup(1_000_000, 50_000, 0.05, 20, 0.03)
    assert grown > flat


def test_years_to_target_reachable():
    yrs = years_to_target(1_000_000, 100_000, 0.05, 20_000_000)
    assert yrs is not None
    assert 10 <= yrs <= 20


def test_years_to_target_already_met():
    assert years_to_target(50_000_000, 0, 0.05, 10_000_000) == 0.0


def test_years_to_target_unreachable():
    # 積立ゼロ・低利回り・極大目標 → 100年以内に未到達
    assert years_to_target(1000, 0, 0.01, 10**12, max_years=100) is None
