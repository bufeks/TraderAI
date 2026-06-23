#!/usr/bin/env bash
# TraderAI 定期自動実行スクリプト(cron / launchd / Task Scheduler 用)。
#
# 「常に自動更新」は OS のスケジューラから本スクリプトを定期実行して実現する。
# アラート条件の評価と日次サマリーを行い、Slack(SLACK_WEBHOOK_URL)へ通知する。
#
# 例) crontab -e に以下を追記:
#   # 平日 9-15時の 30分ごとにアラートを評価
#   */30 9-15 * * 1-5  /path/to/TraderAI/examples/cron_check.sh check  >> ~/traderai.log 2>&1
#   # 毎営業日 16時に純資産サマリーを表示
#   0 16 * * 1-5       /path/to/TraderAI/examples/cron_check.sh daily  >> ~/traderai.log 2>&1
set -euo pipefail

# リポジトリ直下に合わせて調整(venv を使う場合は activate)
cd "$(dirname "$0")/.."
[ -d .venv ] && source .venv/bin/activate

MODE="${1:-check}"

echo "===== $(date '+%Y-%m-%d %H:%M:%S') mode=$MODE ====="
case "$MODE" in
  check)
    traderai alerts check
    ;;
  daily)
    traderai networth
    traderai risk
    ;;
  *)
    echo "usage: cron_check.sh [check|daily]" >&2
    exit 1
    ;;
esac
