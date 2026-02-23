import json
from datetime import date
from unittest.mock import MagicMock, patch

from stock_screener.monitoring.infrastructure.slack_notifier import (
    format_message,
    send_notification,
)


def _make_exit_result(action: str, reason: str = "") -> dict:
    return {
        "ticker": "5599.T",
        "name": "S&J",
        "action": action,
        "reason": reason or f"test: {action}",
        "current_price": 1800,
        "entry_price": 1780,
        "shares": 100,
        "days_held": 45,
        "unrealized_pnl": 2000,
        "unrealized_pnl_pct": 0.0112,
        "stop_loss": 1513,
        "target_price": 2670,
        "max_holding_date": "2026-07-14",
    }


class TestFormatMessage:
    def test_stop_loss_message(self):
        result = _make_exit_result("stop_loss")
        msg = format_message(result, date(2026, 3, 1))
        assert "5599.T" in msg
        assert "stop_loss" in msg.lower() or "損切り" in msg

    def test_target_hit_message(self):
        result = _make_exit_result("target_hit")
        msg = format_message(result, date(2026, 3, 1))
        assert "5599.T" in msg
        assert "target_hit" in msg.lower() or "利確" in msg

    def test_time_stop_message(self):
        result = _make_exit_result("time_stop")
        msg = format_message(result, date(2026, 3, 1))
        assert "5599.T" in msg

    def test_force_sell_message(self):
        result = _make_exit_result("force_sell", "Gate1 REJECT")
        msg = format_message(result, date(2026, 3, 1))
        assert "5599.T" in msg
        assert "Gate1 REJECT" in msg or "force_sell" in msg.lower()

    def test_hold_returns_empty(self):
        result = _make_exit_result("hold")
        msg = format_message(result, date(2026, 3, 1))
        assert msg == ""


class TestSendNotification:
    @patch.dict("os.environ", {"SLACK_BOT_TOKEN": ""}, clear=False)
    def test_returns_false_without_token(self):
        """SLACK_BOT_TOKEN が空の場合は False を返す"""
        with patch.dict("os.environ", {"SLACK_BOT_TOKEN": ""}):
            result = send_notification("test")
        assert result is False

    @patch("stock_screener.monitoring.infrastructure.slack_notifier.urllib.request.urlopen")
    @patch.dict("os.environ", {"SLACK_BOT_TOKEN": "xoxb-test-token"}, clear=False)
    def test_sends_to_chat_post_message(self, mock_urlopen):
        """chat.postMessage API を呼び出す"""
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = json.dumps({"ok": True}).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        result = send_notification("test message")
        assert result is True

        # リクエストの検証
        call_args = mock_urlopen.call_args
        req = call_args[0][0]
        assert req.full_url == "https://slack.com/api/chat.postMessage"
        assert req.get_header("Authorization") == "Bearer xoxb-test-token"
        assert req.get_header("Content-type") == "application/json; charset=utf-8"

        body = json.loads(req.data.decode("utf-8"))
        assert body["text"] == "test message"
        assert body["channel"] == "C04Q3AV4TA5"

    @patch("stock_screener.monitoring.infrastructure.slack_notifier.urllib.request.urlopen")
    @patch.dict("os.environ", {"SLACK_BOT_TOKEN": "xoxb-test-token"}, clear=False)
    def test_returns_false_on_api_error(self, mock_urlopen):
        """API エラー時は False を返す"""
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = json.dumps({"ok": False, "error": "channel_not_found"}).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        result = send_notification("test message")
        assert result is False

    @patch("stock_screener.monitoring.infrastructure.slack_notifier.urllib.request.urlopen")
    @patch.dict("os.environ", {"SLACK_BOT_TOKEN": "xoxb-test-token"}, clear=False)
    def test_returns_false_on_exception(self, mock_urlopen):
        """例外発生時は False を返す"""
        mock_urlopen.side_effect = Exception("network error")

        result = send_notification("test message")
        assert result is False
