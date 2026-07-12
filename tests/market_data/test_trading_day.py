from datetime import date

from stock_screener.market_data.domain.trading_day import is_trading_day


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
