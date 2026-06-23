"""設定の読み込み。環境変数(.env)から各種パラメータを解決する。"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # python-dotenv 未インストールでも動作させる
    pass

DEFAULT_MODEL = "claude-opus-4-8"


@dataclass
class Config:
    """実行時設定。"""

    anthropic_api_key: str | None
    model: str
    portfolio_path: Path
    base_currency: str

    @property
    def accounts_path(self) -> Path:
        """手動評価額(iDeCo・投信など)の保存先。"""
        return self.portfolio_path.with_name("accounts.json")

    @property
    def alerts_path(self) -> Path:
        """アラートルールの保存先。"""
        return self.portfolio_path.with_name("alerts.json")

    @property
    def journal_path(self) -> Path:
        """分析スナップショット(時系列)の保存先。"""
        return self.portfolio_path.with_name("journal.jsonl")

    @property
    def watchlist_path(self) -> Path:
        """ウォッチリストの保存先。"""
        return self.portfolio_path.with_name("watchlist.json")

    @property
    def knowledge_path(self) -> Path:
        """知識ループ(テーゼ・教訓・警告)の保存先。"""
        return self.portfolio_path.with_name("knowledge.jsonl")

    @property
    def settings_path(self) -> Path:
        """ユーザー設定(積立額など)の保存先。"""
        return self.portfolio_path.with_name("settings.json")

    def load_settings(self) -> dict:
        if self.settings_path.exists():
            return json.loads(self.settings_path.read_text(encoding="utf-8"))
        return {}

    def save_settings(self, settings: dict) -> None:
        self.settings_path.parent.mkdir(parents=True, exist_ok=True)
        self.settings_path.write_text(
            json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    @classmethod
    def load(cls) -> "Config":
        portfolio_path = os.environ.get("TRADERAI_PORTFOLIO_PATH")
        if portfolio_path:
            path = Path(portfolio_path).expanduser()
        else:
            path = Path.home() / ".traderai" / "portfolio.json"

        return cls(
            anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY"),
            model=os.environ.get("TRADERAI_MODEL", DEFAULT_MODEL),
            portfolio_path=path,
            base_currency=os.environ.get("TRADERAI_BASE_CURRENCY", "JPY"),
        )
