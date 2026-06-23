"""知識ループ。

投資テーゼ・教訓・失敗パターンを記録し、銘柄分析時に関連する記録を呼び出す。
失敗パターンには任意でトリガー条件(指標・演算子・閾値)を付与でき、現在の
指標がその条件を満たした場合に自動警告する。「使うほど賢くなる」ための蓄積層。
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

KINDS = ("thesis", "lesson", "warning")  # 投資テーゼ / 教訓 / 警告
METRICS = ("price", "change_pct", "rsi", "score")
OPS = ("gt", "lt")


@dataclass
class Trigger:
    metric: str  # price | change_pct | rsi | score
    op: str  # gt | lt
    threshold: float


@dataclass
class Entry:
    text: str
    kind: str = "thesis"
    symbol: str = ""  # 空なら全体に対する記録
    trigger: dict | None = None  # {"metric","op","threshold"}
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def __post_init__(self) -> None:
        if self.kind not in KINDS:
            raise ValueError(f"kind は {KINDS} のいずれか。")
        if self.trigger:
            if self.trigger.get("metric") not in METRICS:
                raise ValueError(f"trigger.metric は {METRICS} のいずれか。")
            if self.trigger.get("op") not in OPS:
                raise ValueError(f"trigger.op は {OPS} のいずれか。")


def _triggered(observed: float, op: str, threshold: float) -> bool:
    return observed > threshold if op == "gt" else observed < threshold


def evaluate_triggers(entries: list[Entry], observed: dict[str, float]) -> list[Entry]:
    """observed(指標名→値)に対しトリガー条件が成立する記録を返す。"""
    hits: list[Entry] = []
    for e in entries:
        if not e.trigger:
            continue
        metric = e.trigger["metric"]
        if metric not in observed or observed[metric] is None:
            continue
        if _triggered(observed[metric], e.trigger["op"], e.trigger["threshold"]):
            hits.append(e)
    return hits


class KnowledgeBase:
    def __init__(self, path: Path):
        self.path = path

    def add(self, entry: Entry) -> Entry:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")
        return entry

    def load(self) -> list[Entry]:
        if not self.path.exists():
            return []
        out: list[Entry] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                out.append(Entry(**json.loads(line)))
        return out

    def for_symbol(self, symbol: str) -> list[Entry]:
        """指定銘柄に紐づく記録 + 全体記録(symbol 空)を返す。"""
        symbol = symbol.upper()
        return [e for e in self.load() if e.symbol.upper() in (symbol, "")]
