"""分析結果の蓄積と活用。

純資産スナップショットを時系列(JSONL)で追記保存し、前回比や推移として
振り返れるようにする。エージェントやレポートから過去データを参照して
「先月比」「資産推移」などの文脈に活用する。
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .accounts import AccountBook


@dataclass
class Snapshot:
    timestamp: str
    total_value: float
    total_cost: float
    total_pl: float
    allocation: dict[str, float] = field(default_factory=dict)
    note: str = ""


class Journal:
    """スナップショットの追記保存と読み出し(JSONL)。"""

    def __init__(self, path: Path):
        self.path = path

    def record(self, book: AccountBook, note: str = "") -> Snapshot:
        snap = Snapshot(
            timestamp=datetime.now(timezone.utc).isoformat(),
            total_value=round(book.total_value(), 2),
            total_cost=round(book.total_cost(), 2),
            total_pl=round(book.total_pl(), 2),
            allocation=book.allocation(),
            note=note,
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(snap), ensure_ascii=False) + "\n")
        return snap

    def load(self) -> list[Snapshot]:
        if not self.path.exists():
            return []
        snaps: list[Snapshot] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                snaps.append(Snapshot(**json.loads(line)))
        return snaps

    def trend(self) -> dict:
        """蓄積されたスナップショットから推移サマリーを返す。"""
        snaps = self.load()
        if not snaps:
            return {"count": 0}
        first, last = snaps[0], snaps[-1]
        change = last.total_value - first.total_value
        change_pct = (
            change / first.total_value * 100 if first.total_value else None
        )
        result = {
            "count": len(snaps),
            "first": {"timestamp": first.timestamp, "total_value": first.total_value},
            "latest": {"timestamp": last.timestamp, "total_value": last.total_value},
            "change": round(change, 2),
            "change_pct": round(change_pct, 2) if change_pct is not None else None,
        }
        if len(snaps) >= 2:
            prev = snaps[-2]
            result["vs_previous"] = round(last.total_value - prev.total_value, 2)
        return result
