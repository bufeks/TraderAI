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
traderai simulate --years 21 --monthly 53000 --rates 3,5,7 --detail
# --principal 未指定なら networth(accounts.json)の合計を元本に使用

# 楽天証券の保有一覧 CSV を取り込む
traderai import-rakuten 保有商品一覧.csv --into portfolio          # 個別株
traderai import-rakuten 投信一覧.csv --into accounts --asset-class 投資信託

# リスク分析(集中度 / 最大ドローダウン)
traderai risk                              # accounts.json の集中度(HHI・実効銘柄数)
traderai risk --drawdown 7011.T --period 2y   # 最大ドローダウン

# 税の概算(iDeCo節税・NISA・ふるさと納税)※確定値ではありません
traderai tax --taxable-income 5931000 --ideco-monthly 23000 --years 21 --resident-income-levy 590500

# リバランス提案(目標配分との乖離 → 売買候補)
traderai rebalance --target "外国株式=35,投資信託=25,国内株式=20,米国株式=10,現金=8,暗号資産=2"

# 節税を織り込んだシミュレーション(iDeCo節税分を再投資した実質利回り)
traderai simulate --years 21 --monthly 53000 --taxable-income 5931000 --ideco-monthly 23000

# 円換算合計は `traderai portfolio` の末尾に表示(USD/JPY 自動換算)
# bitFlyer 残高は公開ティッカーで円建て自動評価(`traderai balances`)

# ストレステスト(相場シナリオでの純資産インパクト)
traderai stress

# バリュースコアで銘柄を採点(PER/PBR/配当/ROE/成長を100点満点)
traderai screen 7203.T 8058.T AAPL

# ウォッチリスト(登録銘柄を現在値+スコアで一覧)
traderai watch add 8058.T --note "三菱商事 気になる"
traderai watch list

# 分析結果の蓄積と活用(純資産スナップショット)
traderai journal snapshot --note "月次記録"   # 現在の純資産を時系列に記録
traderai journal log                          # 履歴・前回比・累計変化を表示

# エージェントと対話(履歴=推移も参照できる)
traderai chat
```

### 自動更新について

| 資産 | 自動更新 |
|------|----------|
| 日本株・米国株(個別) | ✅ コマンド実行のたびに yfinance がライブ株価を取得 |
| 暗号資産(bitFlyer) | ✅ 公開ティッカーで円建て自動評価(API キー設定時) |
| 投資信託・iDeCo | ❌ 公開価格APIが無いため手動 or `import-rakuten` |

「常に(定期)自動実行」は OS のスケジューラから回します。`examples/cron_check.sh`
を cron / launchd に登録すると、アラート評価や日次サマリーを定期通知できます。

```cron
*/30 9-15 * * 1-5  /path/to/TraderAI/examples/cron_check.sh check
0 16 * * 1-5        /path/to/TraderAI/examples/cron_check.sh daily
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
  accounts.py      iDeCo・投信など手動評価額の口座横断集計
  alerts.py        価格・指標アラート(Slack 通知)
  simulation.py    積立による将来資産シミュレーション
  importers.py     楽天証券 CSV 取込
  fx.py            為替換算(USD/JPY)
  risk.py          リスク分析(集中度・相関・DD)
  tax.py           税の概算(iDeCo節税・NISA・課税口座)
  rebalance.py     リバランス提案(目標配分との乖離)
  journal.py       分析結果の蓄積(純資産スナップショット時系列)
  stress.py        ストレステスト(相場シナリオ)
  screener.py      バリュースコア・スクリーナー
  watchlist.py     ウォッチリスト
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
- [x] 通貨換算(USD/JPY)を加味した自動合算(`fx.py` / `portfolio` 円換算合計)
- [x] ポートフォリオのリスク分析(集中度・相関・ドローダウン)(`risk.py` / `traderai risk`)
- [x] 楽天証券 CSV の自動取込フロー(`importers.py` / `traderai import-rakuten`)
- [x] 税の概算(iDeCo節税・NISA)(`tax.py` / `traderai tax`)
- [x] bitFlyer 暗号資産の円建て自動評価 / cron 定期実行(`examples/cron_check.sh`)
- [x] リバランス提案(`rebalance.py` / `traderai rebalance`)
- [x] 節税を織り込んだシミュレーション(`simulate --taxable-income`)
- [x] ふるさと納税の控除上限試算(`tax --resident-income-levy`)
- [x] 分析結果の蓄積と活用(`journal.py` / `traderai journal`)
- [x] ストレステスト(相場シナリオ)(`stress.py` / `traderai stress`)
- [x] バリュースコア・スクリーナー(`screener.py` / `traderai screen`)
- [x] ウォッチリスト(`watchlist.py` / `traderai watch`)
