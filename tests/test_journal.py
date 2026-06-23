from pathlib import Path

from traderai.accounts import AccountBook
from traderai.journal import Journal


def _book(tmp_path: Path, value: float) -> AccountBook:
    book = AccountBook(tmp_path / f"acc_{value}.json")
    book.add("資産", "口座", "外国株式", cost=value * 0.9, value=value)
    return book


def test_record_and_load(tmp_path: Path):
    journal = Journal(tmp_path / "j.jsonl")
    journal.record(_book(tmp_path, 1000), note="初回")
    snaps = journal.load()
    assert len(snaps) == 1
    assert snaps[0].total_value == 1000
    assert snaps[0].note == "初回"


def test_append_multiple(tmp_path: Path):
    journal = Journal(tmp_path / "j.jsonl")
    journal.record(_book(tmp_path, 1000))
    journal.record(_book(tmp_path, 1200))
    journal.record(_book(tmp_path, 1500))
    assert len(journal.load()) == 3


def test_trend(tmp_path: Path):
    journal = Journal(tmp_path / "j.jsonl")
    journal.record(_book(tmp_path, 1000))
    journal.record(_book(tmp_path, 1200))
    journal.record(_book(tmp_path, 1500))
    t = journal.trend()
    assert t["count"] == 3
    assert t["change"] == 500
    assert t["change_pct"] == 50.0
    assert t["vs_previous"] == 300  # 1500 - 1200


def test_trend_empty(tmp_path: Path):
    assert Journal(tmp_path / "none.jsonl").trend() == {"count": 0}
