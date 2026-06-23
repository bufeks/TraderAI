"""楽天証券アダプタ(CSV インポート方式)。

楽天証券は個人向けの公開 REST 売買 API を提供していない(マーケットスピード II の
RSS=Excel 連携はあるが Windows + アプリ常駐が前提)。そのため現実的な連携手段は、
楽天証券サイトからエクスポートできる「保有商品一覧 CSV」を取り込んでポートフォリオへ
反映する方式とする。実発注は本アダプタの対象外。

使い方:
    rakuten = RakutenBroker()
    holdings = rakuten.import_holdings_csv("hoyuu_ichiran.csv")
"""

from __future__ import annotations

import csv
from pathlib import Path

from ..symbols import to_yahoo_symbol
from .base import Balance, Broker, BrokerError, Order


class RakutenBroker(Broker):
    is_live = False  # 実発注は非対応(残高は CSV から取り込む)

    @property
    def name(self) -> str:
        return "rakuten"

    def import_holdings_csv(self, csv_path: str | Path) -> list[Balance]:
        """楽天証券の保有商品一覧 CSV を読み込み、残高として返す。

        列名は CSV のバージョンにより異なるため、「銘柄コード」「保有数量」を含む
        ヘッダーを優先的に探索する。文字コードは Shift_JIS を想定(失敗時 UTF-8)。
        """
        path = Path(csv_path)
        if not path.exists():
            raise BrokerError(f"CSV が見つかりません: {path}")

        for encoding in ("cp932", "utf-8-sig", "utf-8"):
            try:
                text = path.read_text(encoding=encoding)
                break
            except UnicodeDecodeError:
                continue
        else:  # pragma: no cover
            raise BrokerError("CSV の文字コードを判別できませんでした。")

        reader = csv.DictReader(text.splitlines())
        balances: list[Balance] = []
        for row in reader:
            code = _pick(row, ("銘柄コード", "コード", "code"))
            qty = _pick(row, ("保有数量", "数量", "quantity"))
            if not code or not qty:
                continue
            try:
                amount = float(str(qty).replace(",", ""))
            except ValueError:
                continue
            balances.append(
                Balance(asset=to_yahoo_symbol(str(code)), amount=amount)
            )
        return balances

    def get_balances(self) -> list[Balance]:
        raise BrokerError(
            "楽天証券はリアルタイム残高 API 非対応です。import_holdings_csv() を使ってください。"
        )

    def place_order(
        self, symbol: str, side: str, quantity: float, price: float | None = None
    ) -> Order:
        raise BrokerError("楽天証券アダプタは実発注に対応していません。")


def _pick(row: dict, keys: tuple[str, ...]) -> str | None:
    for key in keys:
        for actual in row:
            if actual and key in actual:
                return row[actual]
    return None
