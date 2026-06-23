"""ポートフォリオ管理。

保有銘柄を JSON で永続化し、現在値と評価損益を計算する。
売買は「ペーパートレード(仮想売買)」として記録され、実発注は行わない。
実発注を行う場合は broker アダプタを別途実装し、ここを差し替える想定。
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class Lot:
    """1 回の買い付け(または売り)を表す記録。"""

    symbol: str
    quantity: float
    price: float
    side: str  # "buy" | "sell"
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    note: str = ""


@dataclass
class Position:
    symbol: str
    quantity: float
    avg_cost: float

    def market_value(self, price: float) -> float:
        return self.quantity * price

    def unrealized_pl(self, price: float) -> float:
        return (price - self.avg_cost) * self.quantity

    def unrealized_pl_pct(self, price: float) -> float | None:
        if self.avg_cost == 0:
            return None
        return (price - self.avg_cost) / self.avg_cost * 100


class Portfolio:
    """保有ポジションと取引履歴を管理する。"""

    def __init__(self, path: Path):
        self.path = path
        self.lots: list[Lot] = []
        self._load()

    # --- 永続化 -------------------------------------------------------
    def _load(self) -> None:
        if self.path.exists():
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self.lots = [Lot(**lot) for lot in data.get("lots", [])]

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {"lots": [asdict(lot) for lot in self.lots]}
        self.path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    # --- 取引(ペーパートレード) ------------------------------------
    def record_trade(
        self, symbol: str, quantity: float, price: float, side: str, note: str = ""
    ) -> Lot:
        side = side.lower()
        if side not in ("buy", "sell"):
            raise ValueError("side は 'buy' または 'sell' を指定してください。")
        if quantity <= 0:
            raise ValueError("quantity は正の数を指定してください。")
        lot = Lot(
            symbol=symbol.upper(), quantity=quantity, price=price, side=side, note=note
        )
        self.lots.append(lot)
        self.save()
        return lot

    # --- 集計 ---------------------------------------------------------
    def positions(self) -> list[Position]:
        """取引履歴から現在のポジション(平均取得単価つき)を算出する。"""
        agg: dict[str, dict[str, float]] = {}
        for lot in self.lots:
            state = agg.setdefault(lot.symbol, {"qty": 0.0, "cost": 0.0})
            if lot.side == "buy":
                state["cost"] += lot.quantity * lot.price
                state["qty"] += lot.quantity
            else:  # sell
                # 平均取得単価ベースで取得原価を取り崩す
                if state["qty"] > 0:
                    avg = state["cost"] / state["qty"]
                    state["cost"] -= avg * lot.quantity
                state["qty"] -= lot.quantity

        positions: list[Position] = []
        for symbol, state in agg.items():
            qty = round(state["qty"], 8)
            if qty <= 0:
                continue
            avg_cost = state["cost"] / qty if qty else 0.0
            positions.append(Position(symbol=symbol, quantity=qty, avg_cost=avg_cost))
        return sorted(positions, key=lambda p: p.symbol)
