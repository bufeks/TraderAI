"""iDeCo・投資信託など手動評価額の資産を登録するサンプル。

証券会社/iDeCo の画面に表示される「取得金額」「評価額」を入力する。
ライブ株価が取れない資産(投信・iDeCo・現金)を口座横断で集計するために使う。
下記はダミーです。ご自身の数値に置き換えて実行してください。

    python examples/seed_accounts.py
"""

from traderai.accounts import AccountBook
from traderai.config import Config

# (商品名, 口座, 資産クラス, 取得金額, 評価額)
HOLDINGS = [
    ("全世界株インデックス", "iDeCo", "外国株式", 79073, 86141),
    ("日本株インデックス", "iDeCo", "国内株式", 26838, 30797),
    ("投信積立(つみたて)", "楽天証券", "投資信託", 270000, 304165),
    ("円資金", "楽天証券", "現金", 49619, 49619),
]


def main() -> None:
    config = Config.load()
    book = AccountBook(config.accounts_path)
    for name, account, asset_class, cost, value in HOLDINGS:
        book.add(name, account, asset_class, cost, value)
        print(f"登録: [{account}] {name} 評価 {value:,}")
    print(f"\n保存先: {config.accounts_path}")
    print(f"合計評価額: {book.total_value():,.0f}")


if __name__ == "__main__":
    main()
