from datetime import date

from stock_screener.monitoring.domain.exit_monitor import evaluate_holding
from stock_screener.timing.domain.portfolio import Holding


def _make_holding(**kwargs) -> Holding:
    defaults = {
        "ticker": "5599.T",
        "name": "S&J",
        "shares": 100,
        "entry_price": 1780,
        "entry_date": date(2026, 1, 15),
        "stop_loss": 1513,
        "target_price": 2670,
        "max_holding_date": date(2026, 7, 14),
    }
    defaults.update(kwargs)
    return Holding(**defaults)


class TestEvaluateHolding:
    def test_hold_does_not_need_reevaluation(self):
        holding = _make_holding()
        result = evaluate_holding(holding, current_price=1800, today=date(2026, 3, 1))
        assert result["action"] == "hold"
        assert result["needs_gate_reevaluation"] is False

    def test_stop_loss_does_not_need_reevaluation(self):
        holding = _make_holding()
        result = evaluate_holding(holding, current_price=1500, today=date(2026, 3, 1))
        assert result["action"] == "stop_loss"
        assert result["needs_gate_reevaluation"] is False

    def test_target_hit_needs_reevaluation(self):
        holding = _make_holding()
        result = evaluate_holding(holding, current_price=2700, today=date(2026, 3, 1))
        assert result["action"] == "target_hit"
        assert result["needs_gate_reevaluation"] is True

    def test_time_stop_needs_reevaluation(self):
        holding = _make_holding()
        result = evaluate_holding(holding, current_price=1900, today=date(2026, 7, 15))
        assert result["action"] == "time_stop"
        assert result["needs_gate_reevaluation"] is True

    def test_force_sell_does_not_need_reevaluation(self):
        holding = _make_holding(force_sell_flag=True, force_sell_reason="Gate1 REJECT")
        result = evaluate_holding(holding, current_price=1800, today=date(2026, 3, 1))
        assert result["action"] == "force_sell"
        assert result["needs_gate_reevaluation"] is False
