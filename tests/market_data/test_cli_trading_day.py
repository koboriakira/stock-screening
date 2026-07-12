from __future__ import annotations

import json
from datetime import datetime
from unittest.mock import patch

import pytest

from stock_screener.cli import main


class TestCliTradingDayWeekday:
    def test_weekday_is_trading_day(self, capsys):
        with patch("sys.argv", ["stock-screener", "trading-day", "2026-02-24"]):
            main()
        out = json.loads(capsys.readouterr().out)
        assert out["type"] == "trading-day"
        assert out["count"] == 1
        item = out["items"][0]
        assert item["date"] == "2026-02-24"
        assert item["is_trading_day"] is True
        assert out["source"] == "pandas_market_calendars"


class TestCliTradingDayWeekend:
    def test_saturday_is_not_trading_day(self, capsys):
        with patch("sys.argv", ["stock-screener", "trading-day", "2026-02-21"]):
            main()
        out = json.loads(capsys.readouterr().out)
        assert out["items"][0]["is_trading_day"] is False


class TestCliTradingDayHoliday:
    def test_national_holiday_is_not_trading_day(self, capsys):
        with patch("sys.argv", ["stock-screener", "trading-day", "2026-02-23"]):
            main()
        out = json.loads(capsys.readouterr().out)
        assert out["items"][0]["is_trading_day"] is False


class TestCliTradingDayDefaultDate:
    def test_omitted_date_uses_jst_today(self, capsys):
        class _FixedDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                return cls(2026, 7, 10, 23, 59, tzinfo=tz)

        with (
            patch("sys.argv", ["stock-screener", "trading-day"]),
            patch("stock_screener.cli.datetime", _FixedDateTime),
        ):
            main()
        out = json.loads(capsys.readouterr().out)
        assert out["items"][0]["date"] == "2026-07-10"


class TestCliTradingDayInvalidFormat:
    def test_invalid_format_exits_2(self, capsys):
        with (
            patch("sys.argv", ["stock-screener", "trading-day", "not-a-date"]),
            pytest.raises(SystemExit) as exc_info,
        ):
            main()
        assert exc_info.value.code == 2
        out = json.loads(capsys.readouterr().out)
        assert out["type"] == "error"
        assert out["error"]["code"] == "invalid_argument"
