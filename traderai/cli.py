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
from .market import MarketDataError, get_history, get_quote
from .portfolio import Portfolio


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
    for pos in positions:
        try:
            price = get_quote(pos.symbol).price
            pl = pos.unrealized_pl(price)
            pl_pct = pos.unrealized_pl_pct(price)
            print(
                f"{pos.symbol}: {pos.quantity} 株 @ 平均 {pos.avg_cost:,.2f} / "
                f"現在 {price:,.2f} / 含み損益 {pl:+,.2f} ({pl_pct:+.2f}%)"
            )
        except MarketDataError:
            print(f"{pos.symbol}: {pos.quantity} 株 @ 平均 {pos.avg_cost:,.2f} (現在値取得失敗)")
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
        balances = broker.get_balances()
    except BrokerError as exc:
        print(f"エラー: {exc}", file=sys.stderr)
        return 1
    print("=== bitFlyer 残高 ===")
    for b in balances:
        print(f"  {b.asset}: {b.amount}")
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

    p_chat = sub.add_parser("chat", help="エージェントと対話")
    p_chat.set_defaults(func=_cmd_chat)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
