"""価格・指標トリガーによるアラート(通知)。

ルールを JSON で永続化し、現在値やテクニカル指標と照合して条件成立した
ものを検知する。通知先は Slack Incoming Webhook(環境変数 SLACK_WEBHOOK_URL)を
標準ライブラリのみで叩く。未設定時はコンソール出力にフォールバックする。
"""

from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path

from .analysis import analyze
from .market import MarketDataError, get_history, get_quote

# サポートする指標と比較演算子
METRICS = ("price", "change_pct", "rsi")
OPS = ("gt", "lt")


@dataclass
class AlertRule:
    symbol: str
    metric: str  # "price" | "change_pct" | "rsi"
    op: str  # "gt"(より大きい) | "lt"(より小さい)
    threshold: float
    note: str = ""

    def __post_init__(self) -> None:
        if self.metric not in METRICS:
            raise ValueError(f"metric は {METRICS} のいずれかにしてください。")
        if self.op not in OPS:
            raise ValueError(f"op は {OPS} のいずれかにしてください。")


@dataclass
class AlertHit:
    rule: AlertRule
    observed: float


def _current_metric(symbol: str, metric: str) -> float | None:
    if metric in ("price", "change_pct"):
        q = get_quote(symbol)
        return q.price if metric == "price" else q.change_pct
    if metric == "rsi":
        hist = get_history(symbol, period="6mo")
        return analyze(symbol, hist).rsi_14
    return None


def _triggered(observed: float, op: str, threshold: float) -> bool:
    return observed > threshold if op == "gt" else observed < threshold


class AlertStore:
    """アラートルールの永続化と評価。"""

    def __init__(self, path: Path):
        self.path = path
        self.rules: list[AlertRule] = []
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self.rules = [AlertRule(**r) for r in data.get("rules", [])]

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {"rules": [asdict(r) for r in self.rules]}
        self.path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def add(self, rule: AlertRule) -> None:
        self.rules.append(rule)
        self.save()

    def check(self) -> list[AlertHit]:
        """全ルールを評価し、条件成立したものを返す。"""
        hits: list[AlertHit] = []
        for rule in self.rules:
            try:
                observed = _current_metric(rule.symbol, rule.metric)
            except MarketDataError:
                continue
            if observed is None:
                continue
            if _triggered(observed, rule.op, rule.threshold):
                hits.append(AlertHit(rule=rule, observed=observed))
        return hits


def format_hit(hit: AlertHit) -> str:
    r = hit.rule
    op_label = "≥" if r.op == "gt" else "≤"
    msg = (
        f"🔔 {r.symbol}: {r.metric} = {hit.observed:.2f} "
        f"(条件 {op_label} {r.threshold})"
    )
    if r.note:
        msg += f" — {r.note}"
    return msg


def notify(messages: list[str]) -> None:
    """Slack Webhook へ通知。未設定ならコンソール出力。"""
    if not messages:
        return
    text = "\n".join(messages)
    webhook = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook:
        print(text)
        return
    payload = json.dumps({"text": text}).encode()
    req = urllib.request.Request(
        webhook, data=payload, headers={"Content-Type": "application/json"}
    )
    try:
        urllib.request.urlopen(req, timeout=10)
    except Exception as exc:  # noqa: BLE001
        print(f"Slack 通知に失敗しました({exc})。内容:\n{text}")
