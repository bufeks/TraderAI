from pathlib import Path

import pytest

from traderai.watchlist import Watchlist


def test_add_and_list(tmp_path: Path):
    wl = Watchlist(tmp_path / "w.json")
    wl.add("7203", note="トヨタ")
    assert wl.symbols() == ["7203.T"]  # 4桁コードは .T 付与
    assert wl.items[0].note == "トヨタ"


def test_duplicate_rejected(tmp_path: Path):
    wl = Watchlist(tmp_path / "w.json")
    wl.add("AAPL")
    with pytest.raises(ValueError):
        wl.add("aapl")  # 大文字小文字を正規化して重複検出


def test_remove(tmp_path: Path):
    wl = Watchlist(tmp_path / "w.json")
    wl.add("NVDA")
    assert wl.remove("nvda") is True
    assert wl.symbols() == []
    assert wl.remove("NVDA") is False


def test_persistence(tmp_path: Path):
    path = tmp_path / "w.json"
    Watchlist(path).add("9432", note="NTT")
    reloaded = Watchlist(path)
    assert reloaded.symbols() == ["9432.T"]
