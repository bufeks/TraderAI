from pathlib import Path

from traderai.accounts import AccountBook
from traderai.config import Config
from traderai.report import build_report


def _config(tmp_path: Path) -> Config:
    return Config(
        anthropic_api_key=None,
        model="claude-opus-4-8",
        portfolio_path=tmp_path / "portfolio.json",
        base_currency="JPY",
    )


def test_report_empty(tmp_path: Path):
    text = build_report(_config(tmp_path))
    assert "日次レポート" in text
    assert "特筆事項なし" in text


def test_report_with_networth(tmp_path: Path):
    config = _config(tmp_path)
    book = AccountBook(config.accounts_path)
    book.add("全世界株", "iDeCo", "外国株式", 79073, 86141)
    book.add("日本株", "楽天証券", "国内株式", 100000, 90000)
    text = build_report(config)
    assert "純資産" in text
    assert "最大ストレス" in text
