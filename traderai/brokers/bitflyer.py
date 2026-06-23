"""bitFlyer Lightning API アダプタ(スケルトン)。

bitFlyer は公開された REST API(Lightning API)を提供しており、HMAC-SHA256 署名で
残高取得・発注が可能。ここでは追加依存を増やさないため標準ライブラリのみで実装する。

安全のため:
- 残高取得(get_balances)は読み取り専用。
- place_order は実発注のため、環境変数 BITFLYER_ENABLE_LIVE_ORDERS=1 を
  明示的に設定しない限り送信せず BrokerError を送出する。

API キーは環境変数 BITFLYER_API_KEY / BITFLYER_API_SECRET から読み込む。
ドキュメント: https://lightning.bitflyer.com/docs
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
import urllib.request

from .base import Balance, Broker, BrokerError, Order

API_BASE = "https://api.bitflyer.com"


def public_ticker(product_code: str) -> float:
    """公開ティッカー(認証不要)から最終取引価格(ltp)を返す。

    product_code 例: "BTC_JPY", "ETH_JPY"。
    """
    url = f"{API_BASE}/v1/ticker?product_code={product_code}"
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = json.loads(resp.read().decode())
        return float(data["ltp"])
    except Exception as exc:  # noqa: BLE001
        raise BrokerError(f"bitFlyer ティッカー取得に失敗({product_code}): {exc}") from exc


def value_balances(
    balances: list[Balance], ticker_fn=public_ticker
) -> list[tuple[str, float, float | None]]:
    """残高リストを円建て評価する。

    返り値: (資産, 数量, 円評価額 or None)。価格取得に失敗した銘柄は None。
    ticker_fn を差し替えることでテスト可能。
    """
    out: list[tuple[str, float, float | None]] = []
    for b in balances:
        if b.asset.upper() == "JPY":
            out.append((b.asset, b.amount, b.amount))
            continue
        try:
            ltp = ticker_fn(f"{b.asset.upper()}_JPY")
            out.append((b.asset, b.amount, b.amount * ltp))
        except BrokerError:
            out.append((b.asset, b.amount, None))
    return out


class BitFlyerBroker(Broker):
    is_live = True

    def __init__(
        self, api_key: str | None = None, api_secret: str | None = None
    ):
        self.api_key = api_key or os.environ.get("BITFLYER_API_KEY")
        self.api_secret = api_secret or os.environ.get("BITFLYER_API_SECRET")
        if not self.api_key or not self.api_secret:
            raise BrokerError(
                "BITFLYER_API_KEY / BITFLYER_API_SECRET が未設定です。"
            )

    @property
    def name(self) -> str:
        return "bitflyer"

    def _request(self, method: str, path: str, body: dict | None = None) -> object:
        timestamp = str(int(time.time()))
        body_str = json.dumps(body) if body else ""
        message = timestamp + method + path + body_str
        signature = hmac.new(
            self.api_secret.encode(), message.encode(), hashlib.sha256
        ).hexdigest()
        headers = {
            "ACCESS-KEY": self.api_key,
            "ACCESS-TIMESTAMP": timestamp,
            "ACCESS-SIGN": signature,
            "Content-Type": "application/json",
        }
        req = urllib.request.Request(
            API_BASE + path,
            data=body_str.encode() if body_str else None,
            headers=headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode())
        except Exception as exc:  # noqa: BLE001
            raise BrokerError(f"bitFlyer API 呼び出しに失敗しました: {exc}") from exc

    def get_balances(self) -> list[Balance]:
        data = self._request("GET", "/v1/me/getbalance")
        return [
            Balance(asset=item["currency_code"], amount=float(item["amount"]))
            for item in data
            if float(item.get("amount", 0)) > 0
        ]

    def get_balances_valued(self) -> list[tuple[str, float, float | None]]:
        """残高を公開ティッカーで円建て評価して返す((資産, 数量, 円評価額))。"""
        return value_balances(self.get_balances())

    def place_order(
        self, symbol: str, side: str, quantity: float, price: float | None = None
    ) -> Order:
        if os.environ.get("BITFLYER_ENABLE_LIVE_ORDERS") != "1":
            raise BrokerError(
                "実発注は無効化されています。意図的に有効化する場合のみ "
                "BITFLYER_ENABLE_LIVE_ORDERS=1 を設定してください。"
            )
        body = {
            "product_code": symbol.upper(),  # 例: "BTC_JPY"
            "child_order_type": "MARKET" if price is None else "LIMIT",
            "side": side.upper(),
            "size": quantity,
        }
        if price is not None:
            body["price"] = price
        data = self._request("POST", "/v1/me/sendchildorder", body)
        return Order(
            broker_order_id=str(data.get("child_order_acceptance_id", "")),
            symbol=symbol.upper(),
            side=side.lower(),
            quantity=quantity,
            price=price,
            status="accepted",
        )
