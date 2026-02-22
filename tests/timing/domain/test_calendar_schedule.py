from stock_screener.timing.domain.calendar_schedule import (
    CalendarData,
    DividendInfo,
    EarningsScheduleEntry,
    TickerCalendar,
)


class TestEarningsScheduleEntry:
    def test_create_entry(self):
        e = EarningsScheduleEntry(
            quarter="Q3",
            announced_date="2026-02-12",
            next_date="2026-05-14",
            is_confirmed=False,
        )
        assert e.quarter == "Q3"
        assert e.announced_date == "2026-02-12"
        assert e.next_date == "2026-05-14"
        assert e.is_confirmed is False

    def test_to_dict_roundtrip(self):
        e = EarningsScheduleEntry(
            quarter="FY",
            announced_date="2026-02-13",
            next_date="2026-05-13",
            is_confirmed=False,
        )
        d = e.to_dict()
        restored = EarningsScheduleEntry.from_dict(d)
        assert restored.quarter == e.quarter
        assert restored.next_date == e.next_date


class TestDividendInfo:
    def test_create_with_record_date(self):
        d = DividendInfo(record_date="2026-03-31", amount_per_share=50.0)
        assert d.record_date == "2026-03-31"
        assert d.amount_per_share == 50.0

    def test_create_with_null_values(self):
        d = DividendInfo(record_date=None, amount_per_share=None)
        assert d.record_date is None
        assert d.amount_per_share is None

    def test_to_dict_roundtrip(self):
        d = DividendInfo(record_date="2026-12-31", amount_per_share=None)
        data = d.to_dict()
        restored = DividendInfo.from_dict(data)
        assert restored.record_date == "2026-12-31"
        assert restored.amount_per_share is None


class TestTickerCalendar:
    def test_create_ticker_calendar(self):
        tc = TickerCalendar(
            name="S&J",
            fiscal_year_end="03",
            earnings_schedule=[
                EarningsScheduleEntry(
                    quarter="Q3",
                    announced_date="2026-02-12",
                    next_date="2026-05-14",
                    is_confirmed=False,
                ),
            ],
            dividend=DividendInfo(record_date="2026-03-31", amount_per_share=None),
        )
        assert tc.name == "S&J"
        assert tc.fiscal_year_end == "03"
        assert len(tc.earnings_schedule) == 1
        assert tc.dividend.record_date == "2026-03-31"

    def test_latest_earnings_returns_most_recent(self):
        tc = TickerCalendar(
            name="test",
            fiscal_year_end="03",
            earnings_schedule=[
                EarningsScheduleEntry(
                    quarter="Q2",
                    announced_date="2025-11-10",
                    next_date="2026-02-12",
                    is_confirmed=True,
                ),
                EarningsScheduleEntry(
                    quarter="Q3",
                    announced_date="2026-02-12",
                    next_date="2026-05-14",
                    is_confirmed=False,
                ),
            ],
            dividend=DividendInfo(record_date=None, amount_per_share=None),
        )
        latest = tc.latest_earnings()
        assert latest is not None
        assert latest.quarter == "Q3"

    def test_latest_earnings_returns_none_when_empty(self):
        tc = TickerCalendar(
            name="test",
            fiscal_year_end="03",
            earnings_schedule=[],
            dividend=DividendInfo(record_date=None, amount_per_share=None),
        )
        assert tc.latest_earnings() is None


class TestCalendarData:
    def test_create_calendar_data(self):
        cal = CalendarData(tickers={
            "5599.T": TickerCalendar(
                name="S&J",
                fiscal_year_end="03",
                earnings_schedule=[],
                dividend=DividendInfo(record_date="2026-03-31", amount_per_share=None),
            ),
        })
        assert "5599.T" in cal.tickers
        assert cal.tickers["5599.T"].name == "S&J"

    def test_get_ticker_calendar(self):
        cal = CalendarData(tickers={
            "5599.T": TickerCalendar(
                name="S&J",
                fiscal_year_end="03",
                earnings_schedule=[],
                dividend=DividendInfo(record_date=None, amount_per_share=None),
            ),
        })
        assert cal.get("5599.T") is not None
        assert cal.get("9999.T") is None

    def test_to_dict_roundtrip(self):
        cal = CalendarData(tickers={
            "5599.T": TickerCalendar(
                name="S&J",
                fiscal_year_end="03",
                earnings_schedule=[
                    EarningsScheduleEntry(
                        quarter="Q3",
                        announced_date="2026-02-12",
                        next_date="2026-05-14",
                        is_confirmed=False,
                    ),
                ],
                dividend=DividendInfo(record_date="2026-03-31", amount_per_share=None),
            ),
            "4486.T": TickerCalendar(
                name="ユナイトアンドグロウ",
                fiscal_year_end="12",
                earnings_schedule=[
                    EarningsScheduleEntry(
                        quarter="FY",
                        announced_date="2026-02-13",
                        next_date="2026-05-13",
                        is_confirmed=False,
                    ),
                ],
                dividend=DividendInfo(record_date="2026-12-31", amount_per_share=None),
            ),
        })
        d = cal.to_dict()
        restored = CalendarData.from_dict(d)
        assert len(restored.tickers) == 2
        assert restored.tickers["5599.T"].name == "S&J"
        assert restored.tickers["4486.T"].earnings_schedule[0].quarter == "FY"

    def test_empty_calendar(self):
        cal = CalendarData(tickers={})
        assert len(cal.tickers) == 0
        assert cal.get("5599.T") is None
