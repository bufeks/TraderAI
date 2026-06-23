"""設定の読み込み。環境変数(.env)から各種パラメータを解決する。"""

from __future__ import annotations

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
