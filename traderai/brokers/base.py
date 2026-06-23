"""ブローカー抽象インターフェース。

実発注を伴う連携は、このインターフェースを実装したアダプタを通して行う。
エージェント本体はこの抽象に依存し、具体的な証券会社/取引所を意識しない。
"""

from __future__ import annotations

import abc
from dataclasses import dataclass


class BrokerError(RuntimeError):
    """ブローカー操作に失敗した場合に送出。"""


@dataclass
class Balance:
    """口座残高(通貨または銘柄ごと)。"""

    asset: str
    amount: float


@dataclass
class Order:
    """発注/約定結果。"""

    broker_order_id: str
    symbol: str
    side: str  # "buy" | "sell"
    quantity: float
    price: float | None
    status: str  # "accepted" | "filled" | "rejected" など


class Broker(abc.ABC):
    """すべてのブローカーアダプタが満たすべきインターフェース。"""

    #: 実際の資金が動くか(True の場合は実発注)。
    is_live: bool = False

    @property
    @abc.abstractmethod
    def name(self) -> str:
        ...

    @abc.abstractmethod
    def get_balances(self) -> list[Balance]:
        """口座残高の一覧を返す。"""

    @abc.abstractmethod
    def place_order(
        self, symbol: str, side: str, quantity: float, price: float | None = None
    ) -> Order:
        """注文を発注する。price=None は成行を意味する。"""
