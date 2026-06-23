"""口座横断のネットワース(純資産)集計。

楽天証券の個別株のように現在値を yfinance で取得できる資産だけでなく、
iDeCo や投資信託のように「時価評価額」しか得られない資産も統合して、
資産クラス別・口座別に集計する。これらは手動評価額(取得金額/評価額)で
保持し、別ファイル(既定: ~/.traderai/accounts.json)に永続化する。
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class ManualHolding:
    """ライブ株価を持たない、手動評価額ベースの保有。

    iDeCo・投資信託・現金・暗号資産の概算など、評価額が外部表示でしか
    得られない資産を表す。金額はすべて表示通貨(既定 JPY)。
    """

    name: str
    account: str  # 例: "iDeCo", "楽天証券", "bitFlyer"
    asset_class: str  # 例: "国内株式", "外国株式", "投資信託", "暗号資産", "現金"
    cost: float  # 取得金額
    value: float  # 時価評価額

    @property
    def pl(self) -> float:
        return self.value - self.cost

    @property
    def pl_pct(self) -> float | None:
        if self.cost == 0:
            return None
        return self.pl / self.cost * 100


class AccountBook:
    """手動評価額の保有を口座横断で管理・集計する。"""

    def __init__(self, path: Path):
        self.path = path
        self.holdings: list[ManualHolding] = []
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self.holdings = [ManualHolding(**h) for h in data.get("holdings", [])]

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {"holdings": [asdict(h) for h in self.holdings]}
        self.path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def add(
        self,
        name: str,
        account: str,
        asset_class: str,
        cost: float,
        value: float,
    ) -> ManualHolding:
        holding = ManualHolding(
            name=name,
            account=account,
            asset_class=asset_class,
            cost=cost,
            value=value,
        )
        self.holdings.append(holding)
        self.save()
        return holding

    # --- 集計 ---------------------------------------------------------
    def total_value(self) -> float:
        return sum(h.value for h in self.holdings)

    def total_cost(self) -> float:
        return sum(h.cost for h in self.holdings)

    def total_pl(self) -> float:
        return self.total_value() - self.total_cost()

    def by_asset_class(self) -> dict[str, float]:
        agg: dict[str, float] = defaultdict(float)
        for h in self.holdings:
            agg[h.asset_class] += h.value
        return dict(sorted(agg.items(), key=lambda kv: kv[1], reverse=True))

    def by_account(self) -> dict[str, float]:
        agg: dict[str, float] = defaultdict(float)
        for h in self.holdings:
            agg[h.account] += h.value
        return dict(sorted(agg.items(), key=lambda kv: kv[1], reverse=True))

    def allocation(self) -> dict[str, float]:
        """資産クラス別の構成比(%)。"""
        total = self.total_value()
        if total == 0:
            return {}
        return {
            cls: round(value / total * 100, 1)
            for cls, value in self.by_asset_class().items()
        }
