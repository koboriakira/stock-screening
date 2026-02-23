#!/bin/bash
# daily-monitoring.sh
# cron で毎営業日に実行する日次モニタリングスクリプト
#
# 実行内容:
#   1. monitor    - 保有銘柄の exit 判定 + Slack 通知
#   2. watchlist-check - ウォッチリスト底打ちシグナル検出 + Slack 通知
#
# cron 設定例:
#   0 16 * * 1-5 /Users/koboriakira/git/stock-screening/scripts/daily-monitoring.sh

set -euo pipefail

PROJECT_DIR="$HOME/git/stock-screening"
UV="$HOME/.local/bin/uv"
LOG_DIR="$HOME/.local/share/stock-screener/monitoring/logs"
REPORT_DIR="$HOME/.local/share/stock-screener/monitoring/reports"
SLACK_CHANNEL="C04Q3AV4TA5"
SLACK_API="https://slack.com/api/chat.postMessage"

TODAY=$(date +%Y%m%d)
LOG="$LOG_DIR/daily_${TODAY}.log"

mkdir -p "$LOG_DIR" "$REPORT_DIR"

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

slack_notify() {
  local msg="$1"
  if [ -z "${SLACK_BOT_TOKEN:-}" ]; then
    log "WARN: SLACK_BOT_TOKEN is not set, skipping cron notification"
    return
  fi
  curl -s -X POST "$SLACK_API" \
    -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"channel\":\"$SLACK_CHANNEL\",\"text\":\"$msg\"}" > /dev/null 2>&1
}

# --- 1. monitor (保有銘柄) ---
log "=== monitor start ==="
MONITOR_EXIT=0
$UV run stock-screener monitor >> "$LOG" 2>&1 || MONITOR_EXIT=$?
log "=== monitor end (exit=$MONITOR_EXIT) ==="

# --- 2. watchlist-check ---
log "=== watchlist-check start ==="
WL_EXIT=0
$UV run stock-screener watchlist-check \
  --output "$REPORT_DIR/watchlist_${TODAY}.json" \
  >> "$LOG" 2>&1 || WL_EXIT=$?
log "=== watchlist-check end (exit=$WL_EXIT) ==="

# --- Slack にサマリーを通知 ---
SUMMARY="[cron] daily-monitoring $TODAY"
if [ $MONITOR_EXIT -eq 0 ] && [ $WL_EXIT -eq 0 ]; then
  SUMMARY="$SUMMARY: OK"
else
  SUMMARY="$SUMMARY: monitor=$MONITOR_EXIT, watchlist=$WL_EXIT"
fi
slack_notify "$SUMMARY"

log "=== done ==="
