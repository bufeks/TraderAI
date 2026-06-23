"""コマンドラインインターフェース。

対話モード(チャット)と、いくつかの単発サブコマンドを提供する。
"""

from __future__ import annotations

import argparse
import sys

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

    p_chat = sub.add_parser("chat", help="エージェントと対話")
    p_chat.set_defaults(func=_cmd_chat)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
