from traderai.rebalance import parse_target, rebalance


def test_parse_target():
    t = parse_target("外国株式=40,投資信託=25,現金=35")
    assert t == {"外国株式": 40.0, "投資信託": 25.0, "現金": 35.0}


def test_rebalance_buy_and_sell():
    current = {"国内株式": 700, "外国株式": 100, "現金": 200}  # total 1000
    target = {"国内株式": 40, "外国株式": 40, "現金": 20}
    actions = {a.asset_class: a for a in rebalance(current, target, threshold_pct=0.5)}
    # 国内株式は 70% → 40% で売却(delta < 0)
    assert actions["国内株式"].action == "売却"
    assert actions["国内株式"].delta == 400 - 700
    # 外国株式は 10% → 40% で買い増し
    assert actions["外国株式"].action == "買い増し"
    assert actions["外国株式"].delta == 400 - 100


def test_rebalance_hold_within_threshold():
    current = {"A": 505, "B": 495}  # 50.5% / 49.5%
    target = {"A": 50, "B": 50}
    actions = {a.asset_class: a for a in rebalance(current, target, threshold_pct=1.0)}
    assert actions["A"].action == "維持"
    assert actions["B"].action == "維持"


def test_rebalance_sorted_by_abs_delta():
    current = {"A": 900, "B": 50, "C": 50}
    target = {"A": 33, "B": 33, "C": 34}
    actions = rebalance(current, target)
    # 最大乖離(A)が先頭
    assert actions[0].asset_class == "A"
