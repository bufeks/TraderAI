from pathlib import Path

from traderai.accounts import AccountBook, ManualHolding


def test_manual_holding_pl():
    h = ManualHolding("iDeCo全世界", "iDeCo", "外国株式", cost=79073, value=86141)
    assert h.pl == 7068
    assert round(h.pl_pct, 2) == round(7068 / 79073 * 100, 2)


def test_zero_cost_pl_pct_none():
    h = ManualHolding("現金", "楽天", "現金", cost=0, value=50000)
    assert h.pl_pct is None


def test_aggregation(tmp_path: Path):
    book = AccountBook(tmp_path / "accounts.json")
    book.add("全世界株", "iDeCo", "外国株式", 79073, 86141)
    book.add("日本株インデックス", "iDeCo", "国内株式", 26838, 30797)
    book.add("投信積立", "楽天証券", "投資信託", 270000, 304165)

    assert book.total_value() == 86141 + 30797 + 304165
    assert book.total_pl() == book.total_value() - book.total_cost()

    by_class = book.by_asset_class()
    assert by_class["投資信託"] == 304165
    # 評価額の降順に並ぶ
    assert list(by_class.keys())[0] == "投資信託"

    by_account = book.by_account()
    assert by_account["iDeCo"] == 86141 + 30797


def test_allocation_sums_to_100(tmp_path: Path):
    book = AccountBook(tmp_path / "accounts.json")
    book.add("a", "X", "国内株式", 100, 100)
    book.add("b", "X", "外国株式", 100, 300)
    alloc = book.allocation()
    assert alloc["外国株式"] == 75.0
    assert alloc["国内株式"] == 25.0


def test_persistence(tmp_path: Path):
    path = tmp_path / "accounts.json"
    book = AccountBook(path)
    book.add("全世界株", "iDeCo", "外国株式", 79073, 86141)
    reloaded = AccountBook(path)
    assert len(reloaded.holdings) == 1
    assert reloaded.holdings[0].name == "全世界株"
