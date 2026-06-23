"""ウォッチリスト。

気になる銘柄を登録・管理し、現在値やバリュースコアと連携して一覧表示する。
保存先は portfolio.json と同じディレクトリの watchlist.json。
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .symbols import to_yahoo_symbol


@dataclass
class WatchItem:
    symbol: str
    note: str = ""
    added_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class Watchlist:
    def __init__(self, path: Path):
        self.path = path
        self.items: list[WatchItem] = []
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self.items = [WatchItem(**i) for i in data.get("items", [])]

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {"items": [asdict(i) for i in self.items]}
        self.path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def add(self, symbol: str, note: str = "") -> WatchItem:
        symbol = to_yahoo_symbol(symbol)
        if any(i.symbol == symbol for i in self.items):
            raise ValueError(f"{symbol} は既に登録されています。")
        item = WatchItem(symbol=symbol, note=note)
        self.items.append(item)
        self.save()
        return item

    def remove(self, symbol: str) -> bool:
        symbol = to_yahoo_symbol(symbol)
        before = len(self.items)
        self.items = [i for i in self.items if i.symbol != symbol]
        if len(self.items) != before:
            self.save()
            return True
        return False

    def symbols(self) -> list[str]:
        return [i.symbol for i in self.items]
