from pathlib import Path

import pytest

from traderai.knowledge import Entry, KnowledgeBase, evaluate_triggers


def test_invalid_kind():
    with pytest.raises(ValueError):
        Entry(text="x", kind="bogus")


def test_invalid_trigger_metric():
    with pytest.raises(ValueError):
        Entry(text="x", trigger={"metric": "bogus", "op": "gt", "threshold": 1})


def test_add_and_for_symbol(tmp_path: Path):
    kb = KnowledgeBase(tmp_path / "k.jsonl")
    kb.add(Entry(text="高PERで掴むと痛い", kind="lesson", symbol="NVDA"))
    kb.add(Entry(text="現金比率を保つ", kind="thesis"))  # 全体
    kb.add(Entry(text="別銘柄メモ", symbol="AAPL"))
    found = kb.for_symbol("NVDA")
    texts = {e.text for e in found}
    assert "高PERで掴むと痛い" in texts
    assert "現金比率を保つ" in texts  # 全体記録も含む
    assert "別銘柄メモ" not in texts


def test_evaluate_triggers():
    entries = [
        Entry(text="RSI過熱注意", kind="warning", symbol="NVDA",
              trigger={"metric": "rsi", "op": "gt", "threshold": 75}),
        Entry(text="トリガー無しメモ", kind="thesis", symbol="NVDA"),
    ]
    hits = evaluate_triggers(entries, {"rsi": 80})
    assert len(hits) == 1
    assert hits[0].text == "RSI過熱注意"
    # 閾値未満なら不成立
    assert evaluate_triggers(entries, {"rsi": 50}) == []


def test_evaluate_triggers_missing_metric():
    entries = [
        Entry(text="x", trigger={"metric": "score", "op": "lt", "threshold": 40}),
    ]
    assert evaluate_triggers(entries, {"rsi": 80}) == []  # score 未観測
