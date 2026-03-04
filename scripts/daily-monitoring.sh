#!/bin/bash
# daily-monitoring.sh
# cron で毎営業日に実行する日次モニタリングスクリプト
#
# 実行内容:
#   daily-report --notify で保有銘柄 exit 判定 + ウォッチリストシグナル検出 + Slack サマリー通知
#
# cron 設定例:
#   0 16 * * 1-5 /Users/koboriakira/git/stock-screening/scripts/daily-monitoring.sh

set -euo pipefail

PROJECT_DIR="$HOME/git/stock-screening"
UV="$HOME/.local/bin/uv"
LOG_DIR="$HOME/.local/share/stock-screener/monitoring/logs"

TODAY=$(date +%Y%m%d)
LOG="$LOG_DIR/daily_${TODAY}.log"

mkdir -p "$LOG_DIR"

# .env から環境変数を読み込む
if [ -f "$PROJECT_DIR/.env" ]; then
  set -a
  # shellcheck source=/dev/null
  source "$PROJECT_DIR/.env"
  set +a
fi

cd "$PROJECT_DIR"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >> "$LOG"
}

log "=== daily-report start ==="
$UV run stock-screener daily-report --notify >> "$LOG" 2>&1 || {
  EXIT_CODE=$?
  log "=== daily-report failed (exit=$EXIT_CODE) ==="
  exit $EXIT_CODE
}
log "=== daily-report end ==="
