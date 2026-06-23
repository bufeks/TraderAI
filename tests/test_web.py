from pathlib import Path

from traderai.accounts import AccountBook
from traderai.config import Config
from traderai.journal import Journal
from traderai.web import dashboard_data


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

