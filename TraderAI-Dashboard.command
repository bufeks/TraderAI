#!/bin/bash
# TraderAI ダッシュボード ランチャー(macOS でダブルクリック起動)。
# 初回は依存を自動セットアップし、サーバ起動を待ってブラウザを開く。
# 小さな Terminal ウィンドウが開く。停止は Ctrl-C。

cd "$(dirname "$0")" || exit 1
REPO="$(pwd)"
PORT="${TRADERAI_PORT:-8787}"
LOG="/tmp/traderai_setup.log"

# venv が無ければ作成
if [ ! -x "$REPO/.venv/bin/python" ]; then
  python3 -m venv "$REPO/.venv"
fi
PY="$REPO/.venv/bin/python"
[ -x "$PY" ] || PY="python3"

# 依存が無ければ初回セットアップ
if ! "$PY" -c "import pandas, yfinance, anthropic" >/dev/null 2>&1; then
  echo "初期セットアップ中… 数分かかる場合があります"
  "$PY" -m pip install --upgrade pip setuptools wheel >"$LOG" 2>&1
  "$PY" -m pip install -e "$REPO" >>"$LOG" 2>&1
fi

echo "TraderAI ダッシュボードを起動します ..."
"$PY" -m traderai.cli journal snapshot --note auto >/dev/null 2>&1

( for _ in $(seq 1 90); do
    if curl -s "http://127.0.0.1:${PORT}/data" >/dev/null 2>&1; then
      open "http://127.0.0.1:${PORT}"; break
    fi
    sleep 1
  done ) >/dev/null 2>&1 &

exec "$PY" -m traderai.cli serve --host 127.0.0.1 --port "$PORT"
