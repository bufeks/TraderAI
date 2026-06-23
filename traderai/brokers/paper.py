"""ペーパートレード用ブローカー。

Portfolio を裏側に使い、実際の資金を動かさずに発注を「記録」する既定の実装。
"""

from __future__ import annotations

import uuid

from ..market import MarketDataError, get_quote
from ..portfolio import Portfolio
from .base import Balance, Broker, Order


class PaperBroker(Broker):
    is_live = False

    def __init__(self, portfolio: Portfolio):
        self.portfolio = portfolio

    @property
    def name(self) -> str:
        return "paper"

    def get_balances(self) -> list[Balance]:
        return [
            Balance(asset=pos.symbol, amount=pos.quantity)
            for pos in self.portfolio.positions()
        ]

    def place_order(
        self, symbol: str, side: str, quantity: float, price: float | None = None
    ) -> Order:
        if price is None:
            # 成行は直近値で約定したものとみなす
            try:
                price = get_quote(symbol).price
            except MarketDataError:
                price = 0.0
        lot = self.portfolio.record_trade(
            symbol, quantity, price, side, note="paper order"
        )
        return Order(
            broker_order_id=f"paper-{uuid.uuid4().hex[:8]}",
            symbol=lot.symbol,
            side=lot.side,
            quantity=lot.quantity,
            price=lot.price,
            status="filled",
        )
