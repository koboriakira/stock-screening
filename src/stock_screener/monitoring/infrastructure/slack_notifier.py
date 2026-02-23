from __future__ import annotations

import json
import logging
import os
import urllib.request
from datetime import date

logger = logging.getLogger(__name__)

SLACK_API_URL = "https://slack.com/api/chat.postMessage"
SLACK_CHANNEL = "C04Q3AV4TA5"

_ACTION_LABELS = {
    "stop_loss": "損切り",
    "target_hit": "利確到達",
    "time_stop": "時間軸ストップ",
    "force_sell": "強制売却",
}


def format_message(exit_result: dict, today: date) -> str:
    """exit 判定結果を Slack メッセージ文字列にフォーマットする。

    action が "hold" の場合は空文字を返す。
    """
    action = exit_result["action"]
    if action == "hold":
        return ""

    label = _ACTION_LABELS.get(action, action)
    ticker = exit_result["ticker"]
    name = exit_result.get("name", "")
    current_price = exit_result["current_price"]
    entry_price = exit_result.get("entry_price", 0)
    shares = exit_result.get("shares", 0)
    days_held = exit_result.get("days_held", 0)
    pnl = exit_result.get("unrealized_pnl", 0)
    pnl_pct = exit_result.get("unrealized_pnl_pct", 0)
    reason = exit_result["reason"]

    return (
        f"[{label}] {ticker} ({name})\n"
        f"日付: {today.isoformat()}\n"
        f"現在値: {current_price:,.0f} / 取得価格: {entry_price:,.0f}\n"
        f"保有株数: {shares} / 保有日数: {days_held}日\n"
        f"含み損益: {pnl:+,.0f} ({pnl_pct:+.1%})\n"
        f"理由: {reason}"
    )


def send_notification(message: str) -> bool:
    """Slack Bot Token を使って chat.postMessage API で通知を送信する。

    SLACK_BOT_TOKEN が未設定の場合は False を返す。
    """
    token = os.environ.get("SLACK_BOT_TOKEN", "")
    if not token:
        logger.warning("SLACK_BOT_TOKEN is not set, skipping notification")
        return False

    payload = json.dumps({
        "channel": SLACK_CHANNEL,
        "text": message,
    }).encode("utf-8")

    req = urllib.request.Request(  # noqa: S310
        SLACK_API_URL,
        data=payload,
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310
            body = json.loads(resp.read().decode("utf-8"))
            if body.get("ok"):
                return True
            logger.error("Slack API error: %s", body.get("error", "unknown"))
            return False
    except Exception:
        logger.exception("Slack notification failed")
        return False
