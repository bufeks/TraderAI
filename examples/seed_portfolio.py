"""ポートフォリオへ保有銘柄を一括登録するサンプルスクリプト。

下記はダミーデータです。ご自身の保有銘柄(証券会社アプリの「保有銘柄」画面や
エクスポート CSV)に置き換えて実行してください。日本株は 4 桁コードを使うと
自動で ``.T`` が付与されます。

    python examples/seed_portfolio.py
"""

from traderai.config import Config
from traderai.portfolio import Portfolio
from traderai.symbols import to_yahoo_symbol

# (銘柄コード/ティッカー, 数量, 平均取得単価) のダミー例
HOLDINGS = [
    ("7203", 100, 2500.0),   # 日本株 → 7203.T に変換される
    ("AAPL", 10, 180.0),     # 米国株
    ("BTC-USD", 0.01, 9000000.0),  # 暗号資産
]


def main() -> None:
    config = Config.load()
    pf = Portfolio(config.portfolio_path)
    for code, qty, cost in HOLDINGS:
        symbol = to_yahoo_symbol(code)
        pf.record_trade(symbol, qty, cost, "buy", note="seed")
        print(f"登録: {symbol} {qty} @ {cost}")
    print(f"\n保存先: {config.portfolio_path}")


if __name__ == "__main__":
    main()
