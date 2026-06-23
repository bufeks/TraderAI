from traderai.stress import SCENARIOS, apply_scenario, run_all


def test_apply_scenario_loss():
    values = {"米国株式": 1000, "現金": 1000}
    # 米国株式 -50%、現金 0 → 合計 2000 → 1500、損失 -500、-25%
    r = apply_scenario(values, {"米国株式": -0.50})
    assert r.before == 2000
    assert r.after == 1500
    assert r.loss == -500
    assert r.loss_pct == -25.0


def test_unknown_class_unaffected():
    values = {"国内株式": 500}
    r = apply_scenario(values, {"米国株式": -0.5})
    assert r.after == 500
    assert r.loss == 0


def test_run_all_sorted_worst_first():
    values = {"米国株式": 1000, "暗号資産": 1000, "国内株式": 1000}
    results = run_all(values)
    # 最も損失が大きい(最小の loss)が先頭
    assert results[0].loss <= results[-1].loss
    assert {r.scenario for r in results} == set(SCENARIOS)


def test_each_scenario_nonpositive_loss():
    values = {"国内株式": 100, "米国株式": 100, "暗号資産": 100, "投資信託": 100}
    for r in run_all(values):
        assert r.loss <= 0
