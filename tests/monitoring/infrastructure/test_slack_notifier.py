from datetime import date

from stock_screener.monitoring.infrastructure.slack_notifier import format_message


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
