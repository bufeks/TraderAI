from traderai.graph import related_symbols, symbol_tags, tag_clusters
from traderai.knowledge import Entry


def _entries():
    return [
        Entry(text="GPU需要", symbol="NVDA", tags=["半導体", "AI"]),
        Entry(text="ファウンドリ", symbol="8035.T", tags=["半導体"]),
        Entry(text="高配当", symbol="9432.T", tags=["高配当", "ディフェンシブ"]),
        Entry(text="クラウドAI", symbol="MSFT", tags=["AI"]),
        Entry(text="全体メモ", tags=["マクロ"]),  # symbol なし → 除外
    ]


def test_symbol_tags():
    st = symbol_tags(_entries())
    assert st["NVDA"] == {"半導体", "AI"}
    assert "全体メモ" not in st  # symbol なしは含まない


def test_tag_clusters():
    clusters = tag_clusters(_entries())
    assert clusters["半導体"] == ["8035.T", "NVDA"]
    assert clusters["AI"] == ["MSFT", "NVDA"]


def test_related_symbols():
    rel = related_symbols(_entries(), "NVDA")
    assert rel["半導体"] == ["8035.T"]
    assert rel["AI"] == ["MSFT"]


def test_related_none():
    rel = related_symbols(_entries(), "9432.T")
    # 9432 のタグ(高配当/ディフェンシブ)は他に保有者がいない
    assert rel == {}
