from traderai.screener import Metrics, value_score


def test_high_value_stock_scores_high():
    m = Metrics(per=8, pbr=0.8, dividend_yield=0.045, roe=0.22, revenue_growth=0.25)
    r = value_score("TEST", m)
    assert r.total == 100  # 25+25+20+15+15
    assert r.breakdown["PER"] == 25


def test_expensive_growth_stock_scores_low_on_value():
    m = Metrics(per=80, pbr=20, dividend_yield=0.0, roe=0.40, revenue_growth=0.50)
    r = value_score("NVDA", m)
    assert r.breakdown["PER"] == 0
    assert r.breakdown["PBR"] == 0
    assert r.breakdown["配当利回り"] == 0
    # ROE/成長は満点
    assert r.breakdown["ROE"] == 15
    assert r.breakdown["売上成長率"] == 15
    assert r.total == 30


def test_missing_metrics_score_zero():
    r = value_score("X", Metrics())
    assert r.total == 0


def test_negative_per_scores_zero():
    r = value_score("X", Metrics(per=-5))
    assert r.breakdown["PER"] == 0


def test_mid_tier():
    m = Metrics(per=14, pbr=1.4, dividend_yield=0.025, roe=0.12, revenue_growth=0.07)
    r = value_score("MID", m)
    # 20 + 20 + 11 + 8 + 8
    assert r.total == 67
