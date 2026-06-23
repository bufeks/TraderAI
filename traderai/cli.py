"""コマンドラインインターフェース。

対話モード(チャット)と、いくつかの単発サブコマンドを提供する。
"""

from __future__ import annotations

import argparse
import sys

from .accounts import AccountBook
from .alerts import AlertRule, AlertStore, format_hit, notify
from .analysis import analyze as analyze_history
from .config import Config
from .fx import convert
from .importers import (
    ImportError_,
    import_to_accounts,
    import_to_portfolio,
    parse_rakuten_holdings,
)
from .journal import Journal
from .market import MarketDataError, get_history, get_quote
from .portfolio import Portfolio
from .rebalance import parse_target, rebalance
from .risk import concentration, max_drawdown
from .simulation import future_value_with_tax, project, scenarios
from .tax import (
    TAXABLE_GAIN_RATE,
    combined_marginal_rate,
    furusato_nozei_limit,
    ideco_tax_benefit,
    marginal_income_tax_rate,
)

# リバランスの既定目標配分(例。個別株偏重を是正する方向。--target で上書き可)
DEFAULT_TARGET = "外国株式=35,投資信託=25,国内株式=20,米国株式=10,現金=8,暗号資産=2"


def _cmd_quote(args: argparse.Namespace) -> int:
    try:
        q = get_quote(args.symbol)
    except MarketDataError as exc:
        print(f"エラー: {exc}", file=sys.stderr)
        return 1
    change = f"{q.change_pct:+.2f}%" if q.change_pct is not None else "N/A"
    print(f"{q.symbol}: {q.price:,.2f} {q.currency} (前日比 {change})")
    return 0


def _cmd_analyze(args: argparse.Namespace) -> int:
    try:
        hist = get_history(args.symbol, period=args.period)
    except MarketDataError as exc:
        print(f"エラー: {exc}", file=sys.stderr)
        return 1
    snap = analyze_history(args.symbol, hist)
    print(f"=== {snap.symbol} テクニカル ===")
    print(f"終値        : {snap.last_close:,.2f}")
    print(f"SMA20/50/200: {snap.sma_20} / {snap.sma_50} / {snap.sma_200}")
    print(f"RSI(14)     : {snap.rsi_14}")
    print(f"MACD/Signal : {snap.macd} / {snap.macd_signal}")
    print(f"年率ボラ(%) : {snap.volatility_annual_pct}")
    return 0


def _cmd_portfolio(args: argparse.Namespace) -> int:
    config = Config.load()
    pf = Portfolio(config.portfolio_path)
    positions = pf.positions()
    if not positions:
        print("保有ポジションはありません。")
        return 0
    print(f"=== ポートフォリオ ({config.portfolio_path}) ===")
    total_jpy = 0.0
    fx_failed = False
    for pos in positions:
        try:
            q = get_quote(pos.symbol)
            price = q.price
            pl = pos.unrealized_pl(price)
            pl_pct = pos.unrealized_pl_pct(price)
            print(
                f"{pos.symbol}: {pos.quantity} 株 @ 平均 {pos.avg_cost:,.2f} / "
                f"現在 {price:,.2f} {q.currency} / 含み損益 {pl:+,.2f} ({pl_pct:+.2f}%)"
            )
            try:
                total_jpy += convert(pos.market_value(price), q.currency, "JPY")
            except MarketDataError:
                fx_failed = True
        except MarketDataError:
            print(f"{pos.symbol}: {pos.quantity} 株 @ 平均 {pos.avg_cost:,.2f} (現在値取得失敗)")
    suffix = "(一部為替取得失敗)" if fx_failed else ""
    print(f"\n円換算 評価額合計: {total_jpy:,.0f} JPY {suffix}")
    return 0


def _cmd_risk(args: argparse.Namespace) -> int:
    config = Config.load()
    if args.drawdown:
        try:
            hist = get_history(args.drawdown, period=args.period)
        except MarketDataError as exc:
            print(f"エラー: {exc}", file=sys.stderr)
            return 1
        mdd = max_drawdown(hist["Close"])
        print(f"{args.drawdown}: 最大ドローダウン({args.period}) {mdd:.2f}%")
        return 0

    book = AccountBook(config.accounts_path)
    if not book.holdings:
        print("リスク分析には networth(accounts.json)の登録が必要です。")
        return 0

    # 銘柄(保有)単位の集中度
    by_holding = {h.name: h.value for h in book.holdings}
    con = concentration(by_holding)
    print("=== 集中度(保有単位) ===")
    print(f"HHI: {con.hhi:.3f} / 実効銘柄数: {con.effective_n:.1f}")
    print(f"最大構成比: {con.top_name} = {con.top_weight:.1f}%\n")

    # 資産クラス単位の集中度
    con_cls = concentration(book.by_asset_class())
    print("=== 集中度(資産クラス単位) ===")
    print(f"HHI: {con_cls.hhi:.3f} / 実効クラス数: {con_cls.effective_n:.1f}")
    for cls, w in con_cls.weights.items():
        print(f"  {cls}: {w:.1f}%")
    return 0


def _cmd_networth(args: argparse.Namespace) -> int:
    config = Config.load()
    book = AccountBook(config.accounts_path)
    if not book.holdings:
        print("手動評価額(iDeCo・投信など)の登録はありません。")
        print(f"登録例は examples/seed_accounts.py を参照({config.accounts_path})。")
        return 0
    cur = config.base_currency
    print(f"=== 純資産サマリー({cur}) ===")
    print(f"評価額合計: {book.total_value():,.0f} / 取得合計: {book.total_cost():,.0f}")
    print(f"評価損益  : {book.total_pl():+,.0f}\n")
    print("[資産クラス別]")
    alloc = book.allocation()
    for cls, value in book.by_asset_class().items():
        print(f"  {cls}: {value:,.0f} ({alloc.get(cls, 0)}%)")
    print("\n[口座別]")
    for account, value in book.by_account().items():
        print(f"  {account}: {value:,.0f}")
    return 0


def _cmd_balances(args: argparse.Namespace) -> int:
    from .brokers.base import BrokerError
    from .brokers.bitflyer import BitFlyerBroker

    try:
        broker = BitFlyerBroker()
        valued = broker.get_balances_valued()
    except BrokerError as exc:
        print(f"エラー: {exc}", file=sys.stderr)
        return 1
    print("=== bitFlyer 残高(公開ティッカーで円建て自動評価) ===")
    total = 0.0
    for asset, amount, jpy in valued:
        if jpy is None:
            print(f"  {asset}: {amount} (円評価取得失敗)")
        else:
            print(f"  {asset}: {amount} ≒ {jpy:,.0f} 円")
            total += jpy
    print(f"\n合計: {total:,.0f} 円")
    return 0


def _cmd_alerts(args: argparse.Namespace) -> int:
    config = Config.load()
    store = AlertStore(config.alerts_path)
    if args.action == "add":
        rule = AlertRule(
            symbol=args.symbol,
            metric=args.metric,
            op=args.op,
            threshold=args.threshold,
            note=args.note or "",
        )
        store.add(rule)
        print(f"アラート登録: {rule.symbol} {rule.metric} {rule.op} {rule.threshold}")
        return 0
    if args.action == "list":
        if not store.rules:
            print("登録済みアラートはありません。")
        for r in store.rules:
            print(f"  {r.symbol} {r.metric} {r.op} {r.threshold} {r.note}")
        return 0
    if args.action == "check":
        hits = store.check()
        if not hits:
            print("条件成立したアラートはありません。")
            return 0
        messages = [format_hit(h) for h in hits]
        notify(messages)
        return 0
    return 1


def _cmd_import_rakuten(args: argparse.Namespace) -> int:
    config = Config.load()
    try:
        rows = parse_rakuten_holdings(args.csv)
    except ImportError_ as exc:
        print(f"エラー: {exc}", file=sys.stderr)
        return 1
    print(f"解析: {len(rows)} 件の保有を検出")
    if args.into == "portfolio":
        pf = Portfolio(config.portfolio_path)
        n = import_to_portfolio(rows, pf)
        print(f"Portfolio に {n} 件を取り込みました → {config.portfolio_path}")
    else:
        book = AccountBook(config.accounts_path)
        n = import_to_accounts(rows, book, asset_class=args.asset_class)
        print(f"AccountBook に {n} 件を取り込みました → {config.accounts_path}")
    return 0


def _cmd_simulate(args: argparse.Namespace) -> int:
    config = Config.load()
    principal = args.principal
    if principal is None:
        # 未指定なら手動評価額(accounts.json)の合計を元本に使う
        book = AccountBook(config.accounts_path)
        principal = book.total_value()
        if principal == 0:
            print(
                "元本が不明です。--principal で指定するか、先に networth を登録してください。",
                file=sys.stderr,
            )
            return 1

    rates = tuple(float(x) / 100 for x in args.rates.split(","))
    cur = config.base_currency
    print(f"=== 将来資産シミュレーション({cur}) ===")
    print(f"初期元本: {principal:,.0f} / 毎月積立: {args.monthly:,.0f} / 期間: {args.years}年")
    print(f"想定年利シナリオ: {', '.join(f'{r*100:.0f}%' for r in rates)}\n")

    total_invested = principal + args.monthly * 12 * args.years
    print(f"投資元本合計(積立含む): {total_invested:,.0f}\n")

    # iDeCo 節税分の再投資(任意)
    annual_tax_saving = 0.0
    if args.taxable_income:
        benefit = ideco_tax_benefit(args.ideco_monthly, args.taxable_income, args.years)
        annual_tax_saving = benefit.annual_saving
        print(f"iDeCo 節税(年 約{annual_tax_saving:,.0f}円)を毎年再投資した場合も併記\n")

    results = scenarios(principal, args.monthly, args.years, rates)
    for rate, value in results.items():
        gain = value - total_invested
        line = f"  年利 {rate*100:.0f}%: {value:,.0f}  (運用益 {gain:+,.0f})"
        if annual_tax_saving:
            with_tax = future_value_with_tax(
                principal, args.monthly, rate, args.years, annual_tax_saving
            )
            line += f"  / 節税再投資込み {with_tax:,.0f}"
        print(line)

    if args.detail:
        mid = rates[len(rates) // 2]
        print(f"\n[年次推移 / 年利 {mid*100:.0f}%]")
        for p in project(principal, args.monthly, mid, args.years):
            if p.year % 5 == 0 or p.year == args.years:
                print(f"  {p.year:>2}年目: 評価 {p.value:,.0f} / 元本 {p.invested:,.0f}")
    return 0


def _cmd_tax(args: argparse.Namespace) -> int:
    ti = args.taxable_income
    inc_rate = marginal_income_tax_rate(ti)
    comb = combined_marginal_rate(ti, args.resident_rate)
    print("=== 税の概算(※確定値ではありません。詳細は税理士/公式シミュレータで) ===")
    print(f"課税所得: {ti:,.0f} 円")
    print(f"所得税 限界税率: {inc_rate*100:.0f}% / 住民税: {args.resident_rate*100:.0f}%")
    print(f"合算限界税率: {comb*100:.0f}%\n")

    benefit = ideco_tax_benefit(args.ideco_monthly, ti, args.years, args.resident_rate)
    print(f"[iDeCo 節税概算] 掛金 月{args.ideco_monthly:,.0f}円(年{benefit.annual_contribution:,.0f}円)")
    print(f"  年間節税額: 約 {benefit.annual_saving:,.0f} 円")
    print(f"  {args.years}年間 累計: 約 {benefit.total_saving:,.0f} 円")
    print(f"  → 拠出に対し実質 約{comb*100:.0f}% の即時リターン相当\n")

    print(f"[NISA] 運用益が非課税。課税口座なら利益に約{TAXABLE_GAIN_RATE*100:.1f}%課税。")
    print("  例: 100万円の利益 → 課税口座で約 203,150 円の税、NISA なら 0 円。")

    if args.resident_income_levy:
        limit = furusato_nozei_limit(args.resident_income_levy, inc_rate)
        print(
            f"\n[ふるさと納税] 住民税所得割 {args.resident_income_levy:,.0f}円 → "
            f"控除上限の目安 約 {limit:,.0f} 円(自己負担2,000円)"
        )
    return 0


def _cmd_rebalance(args: argparse.Namespace) -> int:
    config = Config.load()
    book = AccountBook(config.accounts_path)
    if not book.holdings:
        print("リバランスには networth(accounts.json)の登録が必要です。")
        return 1
    target = parse_target(args.target)
    if abs(sum(target.values()) - 100) > 0.5:
        print(f"注意: 目標配分の合計が {sum(target.values()):.0f}% です(100% 推奨)。", file=sys.stderr)
    current = book.by_asset_class()
    actions = rebalance(current, target, threshold_pct=args.threshold)
    print(f"=== リバランス提案(目標: {args.target}) ===")
    print(f"{'資産クラス':<10}{'現在%':>7}{'目標%':>7}{'売買':>8}{'金額':>14}")
    for a in actions:
        sign = "+" if a.delta > 0 else ""
        print(
            f"{a.asset_class:<10}{a.current_pct:>6.1f}%{a.target_pct:>6.1f}%"
            f"{a.action:>8}{sign}{a.delta:>13,.0f}"
        )
    print("\n※ 売買候補の概算です。NISA枠・税・手数料・最低売買単位は別途考慮してください。")
    return 0


def _cmd_journal(args: argparse.Namespace) -> int:
    config = Config.load()
    journal = Journal(config.journal_path)
    if args.action == "snapshot":
        book = AccountBook(config.accounts_path)
        if not book.holdings:
            print("スナップショットには networth(accounts.json)の登録が必要です。", file=sys.stderr)
            return 1
        snap = journal.record(book, note=args.note or "")
        print(f"記録: {snap.timestamp} 評価額 {snap.total_value:,.0f} 円")
        return 0
    if args.action == "log":
        snaps = journal.load()
        if not snaps:
            print("履歴はまだありません。`traderai journal snapshot` で記録してください。")
            return 0
        prev = None
        for s in snaps:
            date = s.timestamp[:10]
            delta = f" (前回比 {s.total_value - prev:+,.0f})" if prev is not None else ""
            print(f"{date}: {s.total_value:,.0f} 円{delta}  {s.note}")
            prev = s.total_value
        t = journal.trend()
        if t.get("change_pct") is not None:
            print(f"\n累計変化: {t['change']:+,.0f} 円 ({t['change_pct']:+.2f}%)")
        return 0
    return 1


def _cmd_chat(args: argparse.Namespace) -> int:
    config = Config.load()
    if not config.anthropic_api_key:
        print("ANTHROPIC_API_KEY が未設定です。.env を作成してください。", file=sys.stderr)
        return 1
    # agent は anthropic に依存するため遅延 import
    from .agent import TraderAgent

    pf = Portfolio(config.portfolio_path)
    agent = TraderAgent(config, pf)
    print("TraderAI チャット(終了は 'exit' または Ctrl-D)")
    print("※ 助言は参考情報です。最終的な投資判断はご自身で行ってください。\n")
    while True:
        try:
            user = input("あなた> ").strip()
        except EOFError:
            print()
            break
        if user.lower() in ("exit", "quit", "終了"):
            break
        if not user:
            continue
        try:
            answer = agent.ask(user)
        except Exception as exc:  # noqa: BLE001
            print(f"エラー: {exc}", file=sys.stderr)
            continue
        print(f"\nTraderAI> {answer}\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="traderai", description="株式運用・資産形成サポートエージェント"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_quote = sub.add_parser("quote", help="現在値を表示")
    p_quote.add_argument("symbol")
    p_quote.set_defaults(func=_cmd_quote)

    p_analyze = sub.add_parser("analyze", help="テクニカル分析を表示")
    p_analyze.add_argument("symbol")
    p_analyze.add_argument("--period", default="6mo")
    p_analyze.set_defaults(func=_cmd_analyze)

    p_pf = sub.add_parser("portfolio", help="保有ポジションと損益を表示")
    p_pf.set_defaults(func=_cmd_portfolio)

    p_nw = sub.add_parser("networth", help="iDeCo・投信を含む口座横断の純資産集計")
    p_nw.set_defaults(func=_cmd_networth)

    p_bal = sub.add_parser("balances", help="bitFlyer 残高を表示(要 API キー)")
    p_bal.set_defaults(func=_cmd_balances)

    p_alert = sub.add_parser("alerts", help="価格・指標アラート")
    alert_sub = p_alert.add_subparsers(dest="action", required=True)
    a_add = alert_sub.add_parser("add", help="アラートを追加")
    a_add.add_argument("symbol")
    a_add.add_argument("--metric", choices=["price", "change_pct", "rsi"], required=True)
    a_add.add_argument("--op", choices=["gt", "lt"], required=True)
    a_add.add_argument("--threshold", type=float, required=True)
    a_add.add_argument("--note", default="")
    a_add.set_defaults(func=_cmd_alerts)
    a_list = alert_sub.add_parser("list", help="アラート一覧")
    a_list.set_defaults(func=_cmd_alerts)
    a_check = alert_sub.add_parser("check", help="アラートを評価して通知")
    a_check.set_defaults(func=_cmd_alerts)

    p_sim = sub.add_parser("simulate", help="積立による将来資産シミュレーション")
    p_sim.add_argument("--principal", type=float, default=None, help="初期元本(未指定なら networth 合計)")
    p_sim.add_argument("--monthly", type=float, default=54000, help="毎月の積立額(既定 54000)")
    p_sim.add_argument("--years", type=int, default=20, help="年数(既定 20)")
    p_sim.add_argument("--rates", default="3,5,7", help="想定年利%をカンマ区切り(既定 3,5,7)")
    p_sim.add_argument("--detail", action="store_true", help="年次推移も表示")
    p_sim.add_argument("--taxable-income", type=float, default=None, help="課税所得(指定するとiDeCo節税の再投資も併記)")
    p_sim.add_argument("--ideco-monthly", type=float, default=23000, help="iDeCo 月額掛金(既定 23000)")
    p_sim.set_defaults(func=_cmd_simulate)

    p_reb = sub.add_parser("rebalance", help="目標配分との乖離からリバランス提案")
    p_reb.add_argument("--target", default=DEFAULT_TARGET, help='目標配分 例: "外国株式=35,投資信託=25,..."')
    p_reb.add_argument("--threshold", type=float, default=1.0, help="維持とみなす乖離%(既定 1.0)")
    p_reb.set_defaults(func=_cmd_rebalance)

    p_imp = sub.add_parser("import-rakuten", help="楽天証券の保有一覧CSVを取り込む")
    p_imp.add_argument("csv", help="保有商品一覧 CSV のパス")
    p_imp.add_argument(
        "--into", choices=["portfolio", "accounts"], default="portfolio",
        help="取込先(個別株=portfolio / 投信など=accounts)",
    )
    p_imp.add_argument("--asset-class", default="投資信託", help="accounts 取込時の資産クラス")
    p_imp.set_defaults(func=_cmd_import_rakuten)

    p_risk = sub.add_parser("risk", help="集中度・最大ドローダウンのリスク分析")
    p_risk.add_argument("--drawdown", help="指定シンボルの最大ドローダウンを計算")
    p_risk.add_argument("--period", default="2y", help="ドローダウン計算の期間")
    p_risk.set_defaults(func=_cmd_risk)

    p_tax = sub.add_parser("tax", help="税の概算(iDeCo節税・NISA)")
    p_tax.add_argument("--taxable-income", type=float, required=True, help="課税所得(円)")
    p_tax.add_argument("--ideco-monthly", type=float, default=23000, help="iDeCo 月額掛金(既定 23000)")
    p_tax.add_argument("--years", type=int, default=21, help="累計を出す年数(既定 21)")
    p_tax.add_argument("--resident-rate", type=float, default=0.10, help="住民税率(既定 0.10)")
    p_tax.add_argument("--resident-income-levy", type=float, default=None, help="住民税所得割額(指定でふるさと納税上限を試算)")
    p_tax.set_defaults(func=_cmd_tax)

    p_jr = sub.add_parser("journal", help="分析結果の蓄積と活用(純資産スナップショット)")
    jr_sub = p_jr.add_subparsers(dest="action", required=True)
    j_snap = jr_sub.add_parser("snapshot", help="現在の純資産を記録")
    j_snap.add_argument("--note", default="")
    j_snap.set_defaults(func=_cmd_journal)
    j_log = jr_sub.add_parser("log", help="履歴と推移を表示")
    j_log.set_defaults(func=_cmd_journal)

    p_chat = sub.add_parser("chat", help="エージェントと対話")
    p_chat.set_defaults(func=_cmd_chat)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
