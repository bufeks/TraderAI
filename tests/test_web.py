from pathlib import Path

import pandas as pd

from traderai import web
from traderai.accounts import AccountBook
from traderai.config import Config
from traderai.journal import Journal
from traderai.portfolio import Portfolio
from traderai.watchlist import Watchlist
from traderai.web import dashboard_data, symbols_data


def _config(tmp_path: Path) -> Config:
    return Config(
        anthropic_api_key=None,
        model="claude-opus-4-8",
        portfolio_path=tmp_path / "portfolio.json",
        base_currency="JPY",
    )


def test_dashboard_data_empty(tmp_path: Path):
    d = dashboard_data(_config(tmp_path))
    assert d["total_value"] == 0
    assert d["trend"] == []
    assert d["currency"] == "JPY"


def test_dashboard_data_with_holdings_and_trend(tmp_path: Path):
    config = _config(tmp_path)
    book = AccountBook(config.accounts_path)
    book.add("全世界株", "iDeCo", "外国株式", 79073, 86141)
    book.add("日本株", "楽天証券", "国内株式", 100000, 120000)
    Journal(config.journal_path).record(book)

    d = dashboard_data(config)
    assert d["total_value"] == 86141 + 120000
    assert set(d["allocation"]) == {"外国株式", "国内株式"}
    assert len(d["trend"]) == 1
    assert d["trend"][0]["value"] == d["total_value"]

    # 充実化フィールド
    assert len(d["holdings"]) == 2
    assert d["holdings"][0]["value"] >= d["holdings"][1]["value"]  # 評価額降順
    assert d["holdings"][0]["pl"] == d["holdings"][0]["value"] - (
        100000 if d["holdings"][0]["name"] == "日本株" else 79073
    )
    assert d["by_account"]["楽天証券"] == 120000
    assert len(d["stress"]) >= 1
    assert all("loss_pct" in s for s in d["stress"])
    assert d["risk"]["effective_n"] > 0
    assert d["risk"]["top_name"] in ("全世界株", "日本株")



def test_dashboard_forecast_field(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("TRADERAI_MONTHLY", "50000")
    monkeypatch.setenv("TRADERAI_FORECAST_YEARS", "10")
    config = _config(tmp_path)
    book = AccountBook(config.accounts_path)
    book.add("株", "口座", "外国株式", 100, 1_000_000)
    f = dashboard_data(config)["forecast"]
    assert f["monthly"] == 50000
    assert f["years"] == 10
    assert len(f["labels"]) == 11           # 0..10
    assert set(f["rates"]) == {"3", "5", "7"}
    assert len(f["rates"]["5"]) == 11
    # 年利が高いほど最終値が大きい
    assert f["rates"]["3"][-1] < f["rates"]["5"][-1] < f["rates"]["7"][-1]


def test_symbols_data(tmp_path: Path, monkeypatch):
    config = _config(tmp_path)
    Portfolio(config.portfolio_path).record_trade("7203.T", 100, 2500.0, "buy")
    Watchlist(config.watchlist_path).add("AAPL")

    # ネットワークを使わないよう get_history をスタブ化
    def fake_history(symbol, period="3mo", interval="1d"):
        prices = [100.0 + i for i in range(40)]
        return pd.DataFrame({"Close": prices})

    monkeypatch.setattr(web, "get_history", fake_history)
    d = symbols_data(config)
    syms = {s["symbol"]: s for s in d["symbols"]}
    assert "7203.T" in syms and "AAPL" in syms
    assert syms["7203.T"]["sources"] == ["保有"]
    assert syms["AAPL"]["sources"] == ["ウォッチ"]
    assert syms["7203.T"]["price"] == 139.0          # 100+39
    assert syms["7203.T"]["change_pct"] is not None
    assert len(syms["7203.T"]["history"]) > 0
    assert syms["7203.T"]["error"] is None


def test_forecast_reads_settings(tmp_path: Path, monkeypatch):
    # 環境変数を無効化し、settings.json から積立額・年数を読むことを確認
    monkeypatch.delenv("TRADERAI_MONTHLY", raising=False)
    monkeypatch.delenv("TRADERAI_FORECAST_YEARS", raising=False)
    config = _config(tmp_path)
    config.save_settings({"monthly_contribution": 53000, "forecast_years": 15})
    book = AccountBook(config.accounts_path)
    book.add("株", "口座", "外国株式", 100, 1_000_000)
    f = dashboard_data(config)["forecast"]
    assert f["monthly"] == 53000
    assert f["years"] == 15
    assert len(f["rates"]["5"]) == 16
