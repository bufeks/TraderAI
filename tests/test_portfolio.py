from pathlib import Path

from traderai.portfolio import Portfolio


def test_buy_creates_position(tmp_path: Path):
    pf = Portfolio(tmp_path / "pf.json")
    pf.record_trade("AAPL", 10, 100.0, "buy")
    positions = pf.positions()
    assert len(positions) == 1
    assert positions[0].symbol == "AAPL"
    assert positions[0].quantity == 10
    assert positions[0].avg_cost == 100.0


def test_average_cost_over_multiple_buys(tmp_path: Path):
    pf = Portfolio(tmp_path / "pf.json")
    pf.record_trade("7203.T", 10, 2000.0, "buy")
    pf.record_trade("7203.T", 10, 3000.0, "buy")
    pos = pf.positions()[0]
    assert pos.quantity == 20
    assert pos.avg_cost == 2500.0


def test_sell_reduces_quantity(tmp_path: Path):
    pf = Portfolio(tmp_path / "pf.json")
    pf.record_trade("BTC-USD", 2, 50000.0, "buy")
    pf.record_trade("BTC-USD", 1, 60000.0, "sell")
    pos = pf.positions()[0]
    assert pos.quantity == 1
    # 平均取得単価は売却後も維持される
    assert pos.avg_cost == 50000.0


def test_full_sell_removes_position(tmp_path: Path):
    pf = Portfolio(tmp_path / "pf.json")
    pf.record_trade("AAPL", 5, 100.0, "buy")
    pf.record_trade("AAPL", 5, 120.0, "sell")
    assert pf.positions() == []


def test_unrealized_pl(tmp_path: Path):
    pf = Portfolio(tmp_path / "pf.json")
    pf.record_trade("AAPL", 10, 100.0, "buy")
    pos = pf.positions()[0]
    assert pos.unrealized_pl(150.0) == 500.0
    assert pos.unrealized_pl_pct(150.0) == 50.0


def test_persistence_round_trip(tmp_path: Path):
    path = tmp_path / "pf.json"
    pf = Portfolio(path)
    pf.record_trade("AAPL", 10, 100.0, "buy")
    reloaded = Portfolio(path)
    assert len(reloaded.lots) == 1
    assert reloaded.positions()[0].symbol == "AAPL"
