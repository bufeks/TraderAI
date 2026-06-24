#!/bin/bash
# TraderAI ダッシュボード ランチャー(macOS でダブルクリック起動)。
# 初回は依存を自動セットアップし、サーバ起動を待ってブラウザを開く。
# セットアップが失敗しても venv を作り直して自動リトライする。
# 小さな Terminal ウィンドウが開く。停止は Ctrl-C。

cd "$(dirname "$0")" || exit 1
REPO="$(pwd)"
PORT="${TRADERAI_PORT:-8787}"
LOG="/tmp/traderai_setup.log"

deps_ok() { "$1" -c "import pandas, yfinance, anthropic" >/dev/null 2>&1; }

install_into() {
  local py="$1"
  "$py" -m pip install --upgrade pip setuptools wheel 2>&1 | tee -a "$LOG"
  "$py" -m pip install -e "$REPO" 2>&1 | tee -a "$LOG"
  deps_ok "$py"
}

PY="$REPO/.venv/bin/python"

if ! [ -x "$PY" ] || ! deps_ok "$PY"; then
  echo "初期セットアップ中… 数分かかる場合があります"
  : >"$LOG"

  if [ -x "$PY" ]; then
    echo "=== try existing venv ===" >>"$LOG"
    install_into "$PY"
  fi

  if ! deps_ok "$PY"; then
    echo "venv を作り直して再試行します ..."
    echo "=== recreate venv ===" >>"$LOG"
    rm -rf "$REPO/.venv"
    python3 -m venv "$REPO/.venv" 2>&1 | tee -a "$LOG"
    PY="$REPO/.venv/bin/python"
    [ -x "$PY" ] && install_into "$PY"
  fi

  if ! deps_ok "$PY"; then
    echo ""
    echo "❌ 依存ライブラリのインストールに失敗しました。上記のエラー(全文: $LOG)を確認してください。"
    echo "Enter で閉じます。"
    read -r _
    exit 1
  fi
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
