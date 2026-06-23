"""シンボル正規化ヘルパー。

楽天証券などの保有一覧は 4 桁の銘柄コード(例: 7203)で表示される。
yfinance は日本株を ``7203.T`` 形式で扱うため、その変換を提供する。
"""

from __future__ import annotations

import re

_JP_CODE = re.compile(r"^\d{4}$")


def to_yahoo_symbol(code: str) -> str:
    """銘柄コード/ティッカーを yfinance 用シンボルに正規化する。

    - 4 桁の数字(日本株/ETF コード)→ ``{code}.T``
    - それ以外(米国株ティッカーなど)→ 大文字化してそのまま
    """
    code = code.strip()
    if _JP_CODE.match(code):
        return f"{code}.T"
    return code.upper()
