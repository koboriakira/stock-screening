from datetime import date, timedelta

from stock_screener.timing.domain.exit_rules import (
    calc_max_holding_date,
    calc_stop_loss,
    calc_target_price,
    check_exit_conditions,
)
from stock_screener.timing.domain.portfolio import Holding


def _make_holding(
    entry_price: float = 1780,
    entry_date: date = date(2026, 1, 15),
    stop_loss: float = 1513,
    target_price: float = 2670,
    max_holding_date: date = date(2026, 7, 14),
) -> Holding:
    return Holding(
        ticker="5599.T",
        name="S&J",
        shares=100,
        entry_price=entry_price,
        entry_date=entry_date,
        stop_loss=stop_loss,
        target_price=target_price,
        max_holding_date=max_holding_date,
    )


class TestCalcStopLoss:
    def test_x01_stop_loss_line(self):
        """T-X01: entry=1,780 -> stop_loss=1,513"""
        assert calc_stop_loss(1780) == 1513.0

    def test_stop_loss_rounding(self):
        """小数点以下の丸め確認"""
        result = calc_stop_loss(1000)
        assert result == 850.0


class TestCalcTargetPrice:
    def test_x02_target_price(self):
        """T-X02: entry=1,780 -> target=2,670"""
        assert calc_target_price(1780) == 2670.0

    def test_target_with_trailing(self):
        """トレイリングカウント=1 の場合"""
        # 1780 * (1 + 0.50 + 0.25*1) = 1780 * 1.75 = 3115
        assert calc_target_price(1780, trailing_count=1) == 3115.0


class TestCalcMaxHoldingDate:
    def test_max_holding_date(self):
        """entry_date + 180日"""
        result = calc_max_holding_date(date(2026, 1, 15))
        assert result == date(2026, 1, 15) + timedelta(days=180)

    def test_with_extension(self):
        """延長1回 = +90日"""
        result = calc_max_holding_date(date(2026, 1, 15), extension_count=1)
        assert result == date(2026, 1, 15) + timedelta(days=270)


class TestCheckExitConditions:
    def test_x03_stop_loss_triggered(self):
        """T-X03: current=1,500 <= stop=1,513 -> stop_loss"""
        holding = _make_holding(stop_loss=1513)
        result = check_exit_conditions(holding, 1500, date(2026, 3, 1))
        assert result["action"] == "stop_loss"

    def test_x04_time_stop(self):
        """T-X04: max_holding_date 超過 -> time_stop"""
        holding = _make_holding(max_holding_date=date(2026, 7, 14))
        result = check_exit_conditions(holding, 1800, date(2026, 7, 15))
        assert result["action"] == "time_stop"

    def test_x05_target_hit(self):
        """T-X05: current=2,700 >= target=2,670 -> target_hit"""
        holding = _make_holding(target_price=2670)
        result = check_exit_conditions(holding, 2700, date(2026, 3, 1))
        assert result["action"] == "target_hit"

    def test_x06_hold(self):
        """T-X06: いずれも未到達 -> hold"""
        holding = _make_holding()
        result = check_exit_conditions(holding, 1800, date(2026, 3, 1))
        assert result["action"] == "hold"

    def test_stop_loss_priority_over_time_stop(self):
        """損切りが時間軸ストップより優先"""
        holding = _make_holding(stop_loss=1513, max_holding_date=date(2026, 7, 14))
        result = check_exit_conditions(holding, 1500, date(2026, 7, 15))
        assert result["action"] == "stop_loss"

    def test_unrealized_pnl_calculation(self):
        """含み損益の計算"""
        holding = _make_holding(entry_price=1780)
        result = check_exit_conditions(holding, 1900, date(2026, 3, 1))
        assert result["unrealized_pnl"] == (1900 - 1780) * 100
        expected_pct = (1900 - 1780) / 1780
        assert abs(result["unrealized_pnl_pct"] - expected_pct) < 0.0001

    def test_result_structure(self):
        """返却値の構造(拡張フィールド含む)"""
        holding = _make_holding()
        result = check_exit_conditions(holding, 1800, date(2026, 3, 1))
        assert "ticker" in result
        assert "action" in result
        assert "reason" in result
        assert "current_price" in result
        assert "unrealized_pnl" in result
        assert "unrealized_pnl_pct" in result
        assert "name" in result
        assert "entry_price" in result
        assert "shares" in result
        assert "days_held" in result
        assert "stop_loss" in result
        assert "target_price" in result
        assert "max_holding_date" in result

    def test_m05_force_sell_highest_priority(self):
        """T-M05: force_sell が全判定より優先される"""
        holding = Holding(
            ticker="5599.T",
            name="S&J",
            shares=100,
            entry_price=1780,
            entry_date=date(2026, 1, 15),
            stop_loss=1513,
            target_price=2670,
            max_holding_date=date(2026, 7, 14),
            force_sell_flag=True,
            force_sell_reason="Gate1再評価でREJECT",
        )
        # stop_loss にも該当する価格だが force_sell が優先
        result = check_exit_conditions(holding, 1500, date(2026, 3, 1))
        assert result["action"] == "force_sell"
        assert "Gate1再評価でREJECT" in result["reason"]

    def test_m06_force_sell_without_reason(self):
        """T-M06: force_sell_reason が None の場合のデフォルトメッセージ"""
        holding = Holding(
            ticker="5599.T",
            name="S&J",
            shares=100,
            entry_price=1780,
            entry_date=date(2026, 1, 15),
            stop_loss=1513,
            target_price=2670,
            max_holding_date=date(2026, 7, 14),
            force_sell_flag=True,
        )
        result = check_exit_conditions(holding, 1800, date(2026, 3, 1))
        assert result["action"] == "force_sell"

    def test_days_held_calculation(self):
        """保有日数の計算"""
        holding = _make_holding(entry_date=date(2026, 1, 15))
        result = check_exit_conditions(holding, 1800, date(2026, 3, 1))
        expected_days = (date(2026, 3, 1) - date(2026, 1, 15)).days
        assert result["days_held"] == expected_days
