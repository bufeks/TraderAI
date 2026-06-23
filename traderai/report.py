"""日次レポート生成。

純資産サマリー・最大ストレス損失・アラート成立・ウォッチリストの知識トリガー
警告を 1 つのテキストに合成する。Slack 配信は alerts.notify を再利用する。
"""

from __future__ import annotations

from .accounts import AccountBook
from .alerts import AlertStore
from .config import Config
from .knowledge import KnowledgeBase, evaluate_triggers
from .market import MarketDataError, get_history, get_quote
from .analysis import analyze
from .screener import fetch_metrics, value_score
from .stress import run_all as stress_run_all
from .watchlist import Watchlist


def _observed(symbol: str) -> dict:
    obs: dict[str, float] = {}
    try:
        q = get_quote(symbol)
        obs["price"] = q.price
        if q.change_pct is not None:
            obs["change_pct"] = q.change_pct
    except MarketDataError:
        pass
    try:
        obs["rsi"] = analyze(symbol, get_history(symbol, period="6mo")).rsi_14
    except MarketDataError:
        pass
    try:
        obs["score"] = value_score(symbol, fetch_metrics(symbol)).total
    except MarketDataError:
        pass
    return obs


def build_report(config: Config) -> str:
    """日次レポート本文を組み立てて返す。"""
    lines: list[str] = ["📊 TraderAI 日次レポート"]

    book = AccountBook(config.accounts_path)
    if book.holdings:
        lines.append(
            f"純資産: {book.total_value():,.0f} 円 / 評価損益 {book.total_pl():+,.0f}"
        )
        worst = stress_run_all(book.by_asset_class())[0]
        lines.append(f"最大ストレス: {worst.scenario} {worst.loss_pct:.1f}% ({worst.loss:,.0f})")

    alerts = AlertStore(config.alerts_path).check()
    if alerts:
        from .alerts import format_hit

        lines.append("アラート:")
        lines += [f"  {format_hit(h)}" for h in alerts]

    # ウォッチリスト + 保有銘柄の知識トリガー警告
    kb = KnowledgeBase(config.knowledge_path)
    symbols = set(Watchlist(config.watchlist_path).symbols())
    warned: list[str] = []
    for symbol in symbols:
        hits = evaluate_triggers(kb.for_symbol(symbol), _observed(symbol))
        warned += [f"  ⚠️ {symbol}: {e.text}" for e in hits]
    if warned:
        lines.append("知識トリガー警告:")
        lines += warned

    if len(lines) == 1:
        lines.append("(特筆事項なし)")
    return "\n".join(lines)
