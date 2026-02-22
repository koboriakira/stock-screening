from __future__ import annotations

import json
import logging
import os
import urllib.request
from datetime import date

logger = logging.getLogger(__name__)

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
    """Slack Webhook に通知を送信する。

    SLACK_WEBHOOK_URL が未設定の場合は False を返す。
    """
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook_url:
        logger.warning("SLACK_WEBHOOK_URL is not set, skipping notification")
        return False

    payload = json.dumps({"text": message}).encode("utf-8")
    req = urllib.request.Request(  # noqa: S310
        webhook_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310
            return resp.status == 200
    except Exception:
        logger.exception("Slack notification failed")
        return False
