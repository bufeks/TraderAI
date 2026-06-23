# TraderAI

Claude を中核にした、**株式運用・資産形成サポートエージェント**です。
日本株・米国株・暗号資産・ETF を対象に、市場データの取得・テクニカル分析・
ポートフォリオ管理・対話による助言を行います。

> ⚠️ **免責**: 本ツールが提供する情報は投資助言ではなく参考情報です。
> 最終的な投資判断はご自身の責任で行ってください。デフォルトの売買は
> **ペーパートレード(仮想記録)**であり、実際の発注は行いません。

## 主な機能

| 機能 | 説明 |
|------|------|
| 市場データ | yfinance 経由で現在値・ヒストリカル OHLCV を取得 |
| テクニカル分析 | SMA(20/50/200)・RSI(14)・MACD・年率ボラティリティ |
| ポートフォリオ管理 | 保有銘柄を JSON 永続化し、平均取得単価・含み損益を算出 |
| 対話エージェント | Claude Opus 4.8 がツールを使って分析・助言(日本語) |
| ブローカー連携 | ペーパー(既定)/ bitFlyer(API)/ 楽天証券(CSV取込)アダプタ |

## セットアップ

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # ANTHROPIC_API_KEY を設定
```

## 使い方

```bash
# 現在値
traderai quote AAPL
traderai quote 7203.T

# テクニカル分析
traderai analyze NVDA --period 1y

# 保有ポートフォリオと損益
traderai portfolio

# iDeCo・投信を含む口座横断の純資産集計
traderai networth

# bitFlyer 残高(要 API キー)
traderai balances

# 価格・指標アラート
traderai alerts add 9432.T --metric price --op gt --threshold 150.49 --note "NTT 取得単価回復"
traderai alerts list
traderai alerts check     # 条件成立を Slack(SLACK_WEBHOOK_URL)へ通知

# 将来資産シミュレーション(積立)
traderai simulate --years 21 --monthly 54000 --rates 3,5,7 --detail
# --principal 未指定なら networth(accounts.json)の合計を元本に使用

# エージェントと対話
traderai chat
```

### iDeCo・投資信託など(ライブ株価が無い資産)

`examples/seed_accounts.py` に取得金額・評価額を入力して実行すると、
`traderai networth` で資産クラス別・口座別に集計できます。

```bash
python examples/seed_accounts.py
```

### ポートフォリオの登録

`examples/seed_portfolio.py` を自分の保有銘柄に書き換えて実行します。
日本株は 4 桁コード(例 `7203`)を渡すと自動で `.T` が付与されます。

```bash
python examples/seed_portfolio.py
```

## シンボル表記

| 対象 | 例 |
|------|-----|
| 日本株 / 国内ETF | `7203.T`(トヨタ)、`1306.T`(TOPIX連動ETF) |
| 米国株 | `AAPL`、`NVDA`、`NEE` |
| 暗号資産 | `BTC-USD`、`ETH-USD` |

## 証券会社・取引所の連携

`traderai/brokers/` に抽象インターフェース(`Broker`)と各アダプタを置いています。

| アダプタ | 状態 | 備考 |
|----------|------|------|
| `PaperBroker` | ✅ 既定 | 仮想売買。実資金は動かない |
| `BitFlyerBroker` | 🟡 残高取得=可 / 発注=要明示有効化 | bitFlyer Lightning API(HMAC認証)。`BITFLYER_API_KEY` / `BITFLYER_API_SECRET` を設定。実発注は `BITFLYER_ENABLE_LIVE_ORDERS=1` 必須 |
| `RakutenBroker` | 🟡 CSV取込のみ | 楽天証券は個人向け公開売買 API が無いため、保有一覧 CSV を取り込む方式 |

## アーキテクチャ

```
traderai/
  config.py        設定(.env)読み込み
  market.py        市場データ取得(yfinance)
  analysis.py      テクニカル指標
  portfolio.py     保有・損益・永続化
  symbols.py       シンボル正規化(4桁コード→.T)
  agent.py         Claude エージェント(tool use)
  cli.py           CLI エントリポイント
  brokers/         証券会社・取引所アダプタ
tests/             ユニットテスト
examples/          サンプルスクリプト
```

## テスト

```bash
pytest -q
```

## ロードマップ(案)

- [x] iDeCo・投信を含む口座横断の純資産集計(`accounts.py` / `traderai networth`)
- [x] 価格・指標トリガーによる通知(Slack)(`alerts.py` / `traderai alerts`)
- [x] bitFlyer 残高のエージェントツール化(`traderai balances` / chat ツール)
- [x] 積立を踏まえた将来資産シミュレーション(`simulation.py` / `traderai simulate`)
- [ ] 通貨換算(USD/JPY)を加味した自動合算
- [ ] ポートフォリオのリスク分析(相関・集中度・ドローダウン)
- [ ] 楽天証券 CSV の自動取込フロー
