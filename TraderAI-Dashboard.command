#!/bin/bash
# TraderAI ダッシュボード ランチャー(macOS でダブルクリック起動)。
# Finder でこのファイルをダブルクリックすると、サーバを起動し、
# 既定ブラウザで http://127.0.0.1:8787 を自動で開く。停止は Ctrl-C。
#
# 初回のみ、Finder で右クリック→「開く」を選ぶ必要がある場合があります
# (Gatekeeper の確認)。

cd "$(dirname "$0")" || exit 1

PORT="${TRADERAI_PORT:-8787}"

# venv の python を優先。無ければ python3 / python を使う。
if [ -x ".venv/bin/python" ]; then
  PY=".venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PY="python3"
else
  PY="python"
fi

echo "TraderAI ダッシュボードを起動します ..."

# 起動済みデータがあれば、開くたびに純資産スナップショットを記録(推移グラフ用)。
"$PY" -m traderai.cli journal snapshot --note auto >/dev/null 2>&1

# サーバ起動の少し後にブラウザを開く。
( sleep 1.5; open "http://127.0.0.1:${PORT}" ) &

# サーバ起動(Ctrl-C で停止)。
exec "$PY" -m traderai.cli serve --port "$PORT"
