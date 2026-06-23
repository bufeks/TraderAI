from pathlib import Path

import pytest

from traderai.accounts import AccountBook
from traderai.importers import (
    ImportError_,
    import_to_accounts,
    import_to_portfolio,
    parse_rakuten_holdings,
)
from traderai.portfolio import Portfolio

STOCK_CSV = """銘柄コード,銘柄名,保有数量,平均取得価額,評価額
7011,三菱重工業,100,3685.20,384600
9432,ＮＴＴ,1000,150.49,143200
"""

FUND_CSV = """ファンド,保有数量,平均取得価額,評価額
eMAXIS Slim 全世界株式(オルカン),79404,34003.32,304165
"""


def _write(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


def test_parse_stocks(tmp_path: Path):
    rows = parse_rakuten_holdings(_write(tmp_path, "s.csv", STOCK_CSV))
    assert len(rows) == 2
    assert rows[0].code == "7011"
    assert rows[0].quantity == 100
    assert rows[0].avg_cost == 3685.20
    assert rows[1].value == 143200


def test_import_to_portfolio(tmp_path: Path):
    rows = parse_rakuten_holdings(_write(tmp_path, "s.csv", STOCK_CSV))
    pf = Portfolio(tmp_path / "pf.json")
    n = import_to_portfolio(rows, pf)
    assert n == 2
    positions = {p.symbol: p for p in pf.positions()}
    # 4桁コードは .T が付与される
    assert "7011.T" in positions
    assert positions["7011.T"].quantity == 100
    assert positions["7011.T"].avg_cost == 3685.20


def test_import_to_accounts(tmp_path: Path):
    rows = parse_rakuten_holdings(_write(tmp_path, "f.csv", FUND_CSV))
    book = AccountBook(tmp_path / "acc.json")
    n = import_to_accounts(rows, book, asset_class="投資信託")
    assert n == 1
    assert book.holdings[0].value == 304165
    assert "オルカン" in book.holdings[0].name


def test_missing_file_raises():
    with pytest.raises(ImportError_):
        parse_rakuten_holdings("/no/such/file.csv")


def test_empty_csv_raises(tmp_path: Path):
    with pytest.raises(ImportError_):
        parse_rakuten_holdings(_write(tmp_path, "e.csv", "col1,col2\n,\n"))
