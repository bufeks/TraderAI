from traderai.simulation import future_value, project, scenarios


def test_zero_return_is_principal_plus_contributions():
    # 年利 0% なら 元本 + 積立総額
    fv = future_value(principal=1_000_000, monthly=50_000, annual_return=0.0, years=10)
    assert fv == 1_000_000 + 50_000 * 12 * 10


def test_positive_return_exceeds_invested():
    invested = 1_000_000 + 50_000 * 12 * 20
    fv = future_value(1_000_000, 50_000, 0.05, 20)
    assert fv > invested


def test_lump_sum_compounding():
    # 積立なし、100万円を年5%で1年 → 月次複利でほぼ +5%
    fv = future_value(1_000_000, 0, 0.05, 1)
    assert 1_050_000 < fv < 1_052_000


def test_project_length_and_endpoints():
    points = project(1_000_000, 50_000, 0.05, 10)
    assert len(points) == 11  # 0..10
    assert points[0].year == 0
    assert points[0].value == 1_000_000
    assert points[-1].year == 10
    # invested は初期元本 + 累計積立
    assert points[10].invested == 1_000_000 + 50_000 * 12 * 10


def test_scenarios_monotonic():
    res = scenarios(1_000_000, 50_000, 20, rates=(0.03, 0.05, 0.07))
    values = list(res.values())
    # 年利が高いほど最終評価額も大きい
    assert values[0] < values[1] < values[2]
