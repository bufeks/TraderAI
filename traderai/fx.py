"""為替換算。

yfinance の為替シンボル(例: ``USDJPY=X``)を用いて、外貨建ての金額を
円換算する。米国株のように現在値が USD で返る資産を、ポートフォリオ全体の
円ベース合算に組み込むために使う。
"""

from __future__ import annotations

from functools import lru_cache

from .market import get_quote


@lru_cache(maxsize=32)
def fx_rate(base: str, quote: str = "JPY") -> float:
    """1 単位の base 通貨が quote 通貨で何になるかを返す(例: USD→JPY)。"""
    base = base.upper()
    quote = quote.upper()
    if base == quote:
        return 1.0
    return get_quote(f"{base}{quote}=X").price


def convert(amount: float, currency: str, to: str = "JPY") -> float:
    """amount(currency 建て)を to 通貨へ換算する。"""
    currency = currency.upper()
    to = to.upper()
    if currency == to:
        return amount
    return amount * fx_rate(currency, to)
