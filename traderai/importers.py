"""保有データの取込(インポート)。

楽天証券の「保有商品一覧」CSV を解析し、個別株は Portfolio に、
投資信託など評価額ベースの資産は AccountBook に取り込む。
CSV のヘッダー名はバージョンにより異なるため、キーワード一致で列を推定する。
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from .accounts import AccountBook
from .portfolio import Portfolio
from .symbols import to_yahoo_symbol


class ImportError_(RuntimeError):
    """取込に失敗した場合に送出。"""


@dataclass
class RakutenRow:
    code: str  # 銘柄コード or ティッカー
    name: str
    quantity: float
    avg_cost: float | None
    value: float | None  # 評価額(あれば)


def _read_text(path: Path) -> str:
    for encoding in ("cp932", "utf-8-sig", "utf-8"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    raise ImportError_("CSV の文字コードを判別できませんでした(cp932/utf-8)。")


def _pick(row: dict, keys: tuple[str, ...]) -> str | None:
    for key in keys:
        for actual in row:
            if actual and key in actual:
                val = row[actual]
                if val not in (None, ""):
                    return val
    return None


def _to_float(value: str | None) -> float | None:
    if value is None:
        return None
    cleaned = str(value).replace(",", "").replace("円", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_rakuten_holdings(path: str | Path) -> list[RakutenRow]:
    """楽天証券の保有一覧 CSV を解析して行を返す。"""
    path = Path(path)
    if not path.exists():
        raise ImportError_(f"CSV が見つかりません: {path}")

    reader = csv.DictReader(_read_text(path).splitlines())
    rows: list[RakutenRow] = []
    for raw in reader:
        code = _pick(raw, ("銘柄コード", "コード", "ティッカー", "code"))
        name = _pick(raw, ("銘柄名", "ファンド", "商品名", "銘柄", "name"))
        qty = _to_float(_pick(raw, ("保有数量", "数量", "口数", "quantity")))
        avg = _to_float(_pick(raw, ("平均取得価額", "取得単価", "平均取得", "取得価額")))
        value = _to_float(_pick(raw, ("評価額", "時価評価額", "現在値（評価額）")))
        if not (code or name) or qty is None:
            continue
        rows.append(
            RakutenRow(
                code=(code or name or "").strip(),
                name=(name or code or "").strip(),
                quantity=qty,
                avg_cost=avg,
                value=value,
            )
        )
    if not rows:
        raise ImportError_("取込可能な行が見つかりませんでした(列名を確認してください)。")
    return rows


def import_to_portfolio(rows: list[RakutenRow], portfolio: Portfolio) -> int:
    """個別株の行を Portfolio に buy ロットとして取り込む。取得件数を返す。"""
    count = 0
    for row in rows:
        if row.avg_cost is None:
            continue
        symbol = to_yahoo_symbol(row.code)
        portfolio.record_trade(
            symbol, row.quantity, row.avg_cost, "buy", note="rakuten csv import"
        )
        count += 1
    return count


def import_to_accounts(
    rows: list[RakutenRow], book: AccountBook, asset_class: str = "投資信託"
) -> int:
    """評価額のある行を AccountBook(手動評価額)に取り込む。取得件数を返す。"""
    count = 0
    for row in rows:
        if row.value is None:
            continue
        cost = row.avg_cost * row.quantity if row.avg_cost is not None else row.value
        book.add(
            name=row.name,
            account="楽天証券",
            asset_class=asset_class,
            cost=cost,
            value=row.value,
        )
        count += 1
    return count
