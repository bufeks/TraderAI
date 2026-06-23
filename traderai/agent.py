"""Claude を中核にしたエージェント。

Anthropic SDK の tool runner を使い、市場データ取得・テクニカル分析・
ポートフォリオ参照/仮想売買をツールとして提供する。デフォルトは助言と
ペーパートレードに限定し、実発注は行わない。
"""

from __future__ import annotations

import json

import anthropic
from anthropic import beta_tool

from .accounts import AccountBook
from .analysis import analyze as analyze_history
from .config import Config
from .market import MarketDataError, get_history, get_quote
from .portfolio import Portfolio

SYSTEM_PROMPT = """\
あなたは日本の個人投資家の株式運用・資産形成をサポートする AI アシスタント「TraderAI」です。
日本株・米国株・暗号資産・ETF を対象に、提供されたツールを使って最新の市場データと
ユーザーのポートフォリオを確認し、根拠を示しながら分かりやすく助言します。

重要な原則:
- あなたは投資助言の最終判断者ではありません。最終的な投資判断は必ずユーザー自身が行います。
- 推測ではなく、必ずツールで取得した実データに基づいて述べてください。データが取れない
  場合は「取得できなかった」と正直に伝えます。
- 売買ツール(record_trade)は「仮想(ペーパー)記録」であり、実際の発注ではないことを
  必ずユーザーに明示してください。
- 断定的な利益保証はせず、リスク(ボラティリティ、下落シナリオ)も併せて示します。
- 数値は通貨・単位を明記し、要点を先に、根拠を後に簡潔に伝えます。

回答は日本語で行ってください。
"""


def build_tools(portfolio: Portfolio, config: Config | None = None):
    """ポートフォリオに束ねたツール群を生成して返す。"""

    @beta_tool
    def quote(symbol: str) -> str:
        """指定シンボルの現在値(直近値)と前日比を取得する。

        Args:
            symbol: ティッカー。日本株は "7203.T"、米国株は "AAPL"、暗号資産は "BTC-USD" 形式。
        """
        try:
            q = get_quote(symbol)
        except MarketDataError as exc:
            return f"エラー: {exc}"
        return json.dumps(
            {
                "symbol": q.symbol,
                "price": q.price,
                "currency": q.currency,
                "previous_close": q.previous_close,
                "change_pct": q.change_pct,
            },
            ensure_ascii=False,
        )

    @beta_tool
    def technicals(symbol: str, period: str = "6mo") -> str:
        """テクニカル指標(SMA20/50/200・RSI14・MACD・年率ボラティリティ)を計算する。

        Args:
            symbol: ティッカー(quote と同形式)。
            period: 取得期間。1mo, 3mo, 6mo, 1y, 2y, 5y, max のいずれか。
        """
        try:
            hist = get_history(symbol, period=period)
        except MarketDataError as exc:
            return f"エラー: {exc}"
        snapshot = analyze_history(symbol, hist)
        return json.dumps(snapshot.to_dict(), ensure_ascii=False)

    @beta_tool
    def portfolio_summary() -> str:
        """現在の保有ポジションと評価損益(現在値ベース)を取得する。"""
        positions = portfolio.positions()
        if not positions:
            return json.dumps({"positions": [], "note": "保有ポジションはありません。"}, ensure_ascii=False)

        rows = []
        total_value = 0.0
        total_cost = 0.0
        for pos in positions:
            try:
                price = get_quote(pos.symbol).price
            except MarketDataError:
                price = None
            row = {
                "symbol": pos.symbol,
                "quantity": pos.quantity,
                "avg_cost": round(pos.avg_cost, 4),
            }
            if price is not None:
                row["price"] = price
                row["market_value"] = round(pos.market_value(price), 2)
                row["unrealized_pl"] = round(pos.unrealized_pl(price), 2)
                row["unrealized_pl_pct"] = (
                    round(pos.unrealized_pl_pct(price), 2)
                    if pos.unrealized_pl_pct(price) is not None
                    else None
                )
                total_value += pos.market_value(price)
                total_cost += pos.avg_cost * pos.quantity
            rows.append(row)

        return json.dumps(
            {
                "positions": rows,
                "total_market_value": round(total_value, 2),
                "total_cost": round(total_cost, 2),
                "total_unrealized_pl": round(total_value - total_cost, 2),
            },
            ensure_ascii=False,
        )

    @beta_tool
    def record_trade(symbol: str, quantity: float, price: float, side: str) -> str:
        """仮想(ペーパー)売買を記録する。実際の発注は行わない。

        Args:
            symbol: ティッカー。
            quantity: 数量(正の数)。
            price: 約定価格。
            side: "buy"(買い)または "sell"(売り)。
        """
        try:
            lot = portfolio.record_trade(symbol, quantity, price, side)
        except ValueError as exc:
            return f"エラー: {exc}"
        return json.dumps(
            {
                "recorded": True,
                "paper_trade": True,
                "symbol": lot.symbol,
                "quantity": lot.quantity,
                "price": lot.price,
                "side": lot.side,
            },
            ensure_ascii=False,
        )

    @beta_tool
    def net_worth() -> str:
        """iDeCo・投資信託・現金など手動評価額の資産を含む、口座横断の純資産集計を取得する。"""
        if config is None:
            return json.dumps({"error": "設定が未提供のため集計できません。"}, ensure_ascii=False)
        book = AccountBook(config.accounts_path)
        if not book.holdings:
            return json.dumps(
                {"holdings": [], "note": "手動評価額の登録はありません。"},
                ensure_ascii=False,
            )
        return json.dumps(
            {
                "total_value": round(book.total_value(), 2),
                "total_cost": round(book.total_cost(), 2),
                "total_pl": round(book.total_pl(), 2),
                "by_asset_class": {k: round(v, 2) for k, v in book.by_asset_class().items()},
                "by_account": {k: round(v, 2) for k, v in book.by_account().items()},
                "allocation_pct": book.allocation(),
            },
            ensure_ascii=False,
        )

    @beta_tool
    def history() -> str:
        """蓄積された純資産スナップショットの推移(前回比・累計変化)を取得する。"""
        if config is None:
            return json.dumps({"error": "設定が未提供です。"}, ensure_ascii=False)
        from .journal import Journal

        trend = Journal(config.journal_path).trend()
        return json.dumps(trend, ensure_ascii=False)

    @beta_tool
    def knowledge(symbol: str) -> str:
        """指定銘柄に関する過去の投資テーゼ・教訓・失敗パターン(警告)を取得する。

        Args:
            symbol: ティッカー。
        """
        if config is None:
            return json.dumps({"error": "設定が未提供です。"}, ensure_ascii=False)
        from .knowledge import KnowledgeBase

        entries = KnowledgeBase(config.knowledge_path).for_symbol(symbol)
        return json.dumps(
            [
                {"kind": e.kind, "symbol": e.symbol, "text": e.text, "trigger": e.trigger}
                for e in entries
            ],
            ensure_ascii=False,
        )

    tools = [quote, technicals, portfolio_summary, record_trade, net_worth, history, knowledge]

    # bitFlyer の API キーが設定されている場合のみ残高取得ツールを追加
    import os

    if os.environ.get("BITFLYER_API_KEY") and os.environ.get("BITFLYER_API_SECRET"):

        @beta_tool
        def bitflyer_balances() -> str:
            """bitFlyer 口座の暗号資産残高(数量)を取得する(読み取り専用)。"""
            from .brokers.bitflyer import BitFlyerBroker
            from .brokers.base import BrokerError

            try:
                broker = BitFlyerBroker()
                balances = broker.get_balances()
            except BrokerError as exc:
                return f"エラー: {exc}"
            return json.dumps(
                [{"asset": b.asset, "amount": b.amount} for b in balances],
                ensure_ascii=False,
            )

        tools.append(bitflyer_balances)

    return tools


class TraderAgent:
    """会話履歴を保持しながら Claude と対話するエージェント。"""

    def __init__(self, config: Config, portfolio: Portfolio):
        if not config.anthropic_api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY が設定されていません。.env を確認してください。"
            )
        self.config = config
        self.portfolio = portfolio
        self.client = anthropic.Anthropic(api_key=config.anthropic_api_key)
        self.tools = build_tools(portfolio, config)
        self.messages: list[dict] = []

    def ask(self, user_message: str) -> str:
        """ユーザー発話を送り、ツール実行ループを回して最終回答を返す。"""
        self.messages.append({"role": "user", "content": user_message})

        runner = self.client.beta.messages.tool_runner(
            model=self.config.model,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            thinking={"type": "adaptive"},
            tools=self.tools,
            messages=self.messages,
        )

        final = None
        for message in runner:
            final = message

        if final is None:
            return "(応答が得られませんでした)"

        answer = "".join(
            block.text for block in final.content if block.type == "text"
        )
        # 会話履歴には最終的なアシスタント発話のみを残す(ツール往復は内部で完結)。
        # これにより次ターンへ有効な履歴を引き継ぎつつ、宙ぶらりんの tool_use を残さない。
        self.messages.append({"role": "assistant", "content": answer})

        return answer
