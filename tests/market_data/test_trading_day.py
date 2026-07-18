from datetime import date, time

from stock_screener.market_data.domain.trading_day import (
    is_trading_day,
    market_open_close,
    n_trading_days_after,
    next_trading_day,
)


class TestIsTradingDay:
    def test_weekday_is_trading_day(self):
        """2026-02-24 は火曜日 -> 営業日"""
        assert is_trading_day(date(2026, 2, 24)) is True

    def test_saturday_is_not_trading_day(self):
        """土曜日は非営業日"""
        assert is_trading_day(date(2026, 2, 21)) is False

    def test_sunday_is_not_trading_day(self):
        """日曜日は非営業日"""
        assert is_trading_day(date(2026, 2, 22)) is False

    def test_national_holiday_is_not_trading_day(self):
        """天皇誕生日(2/23)は非営業日"""
        assert is_trading_day(date(2026, 2, 23)) is False

    def test_new_years_day_is_not_trading_day(self):
        """元日は非営業日"""
        assert is_trading_day(date(2026, 1, 1)) is False

    def test_regular_friday_is_trading_day(self):
        """通常の金曜日は営業日"""
        assert is_trading_day(date(2026, 2, 20)) is True


class TestNextTradingDay:
    def test_friday_next_is_tuesday_across_holiday(self):
        """金曜(2/20)の翌営業日は、土日と天皇誕生日(2/23)を跨いで火曜(2/24)"""
        assert next_trading_day(date(2026, 2, 20)) == date(2026, 2, 24)

    def test_regular_weekday_next_is_following_day(self):
        """通常の平日の翌営業日は翌日"""
        assert next_trading_day(date(2026, 2, 24)) == date(2026, 2, 25)

    def test_target_itself_not_included(self):
        """target 自体は結果に含まれない(翌営業日は target より後)"""
        assert next_trading_day(date(2026, 2, 24)) > date(2026, 2, 24)


class TestNTradingDaysAfter:
    def test_n_equals_1_matches_next_trading_day(self):
        """n=1 は next_trading_day と一致する"""
        target = date(2026, 2, 20)
        assert n_trading_days_after(target, 1) == next_trading_day(target)

    def test_n_equals_5_crosses_week_boundary(self):
        """金曜(2/20)から5営業日後は週を跨いで 3/2 になる"""
        assert n_trading_days_after(date(2026, 2, 20), 5) == date(2026, 3, 2)


class TestMarketOpenClose:
    def test_weekday_returns_open_and_close_jst(self):
        """平日は 9:00 / 15:30 JST 程度の寄付・引け時刻を返す"""
        result = market_open_close(date(2026, 2, 24))
        assert result is not None
        open_time, close_time = result
        assert open_time == time(9, 0)
        assert close_time == time(15, 30)

    def test_non_trading_day_returns_none(self):
        """非営業日は None を返す"""
        assert market_open_close(date(2026, 2, 21)) is None
