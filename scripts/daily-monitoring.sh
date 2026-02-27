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
MONITOR_OUT=$($UV run stock-screener monitor 2>&1) || MONITOR_EXIT=$?
echo "$MONITOR_OUT" >> "$LOG"
log "=== monitor end (exit=$MONITOR_EXIT) ==="

# monitor 結果から銘柄行を抽出（例: "  4486.T: hold (-0.7%)"）
MONITOR_LINES=$(echo "$MONITOR_OUT" | grep -E '^\s+[0-9]{4}\.T:' || true)

# --- 2. watchlist-check ---
log "=== watchlist-check start ==="
WL_EXIT=0
WL_OUT=$($UV run stock-screener watchlist-check \
  --output "$REPORT_DIR/watchlist_${TODAY}.json" 2>&1) || WL_EXIT=$?
echo "$WL_OUT" >> "$LOG"
log "=== watchlist-check end (exit=$WL_EXIT) ==="

# watchlist 結果からテーブル行を抽出（例: "5599.T  S&J  1/5 ..."）
WL_LINES=$(echo "$WL_OUT" | grep -E '^[0-9]{4}\.T' || true)

# --- Slack にサマリーを通知 ---
SUMMARY="[日次モニタリング $(date +%m/%d)]"

if [ $MONITOR_EXIT -ne 0 ] || [ $WL_EXIT -ne 0 ]; then
  SUMMARY="$SUMMARY ⚠️ エラーあり (monitor=$MONITOR_EXIT, watchlist=$WL_EXIT)"
fi

# 保有銘柄セクション
SUMMARY="$SUMMARY\n■ 保有銘柄"
if [ -n "$MONITOR_LINES" ]; then
  while IFS= read -r line; do
    SUMMARY="$SUMMARY\n$(echo "$line" | sed 's/^[[:space:]]*/・/')"
  done <<< "$MONITOR_LINES"
else
  SUMMARY="$SUMMARY\n・対象なし"
fi

# ウォッチリストセクション
SUMMARY="$SUMMARY\n■ ウォッチリスト"
if [ -n "$WL_LINES" ]; then
  while IFS= read -r line; do
    # テーブル行からティッカー、名前、スコア、変動率を抽出
    ticker=$(echo "$line" | awk '{print $1}')
    name=$(echo "$line" | awk '{print $2}')
    score=$(echo "$line" | awk '{print $3}')
    delta=$(echo "$line" | awk '{print $4}')
    price=$(echo "$line" | awk '{print $5}')
    chg=$(echo "$line" | awk '{print $6}')
    SUMMARY="$SUMMARY\n・${ticker} ${name} ${price}円(${chg}%) スコア${score}(${delta})"
  done <<< "$WL_LINES"
else
  SUMMARY="$SUMMARY\n・対象なし"
fi

slack_notify "$(echo -e "$SUMMARY")"

log "=== done ==="
