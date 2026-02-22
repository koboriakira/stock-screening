from stock_screener.timing.domain.calendar_schedule import (
    CalendarData,
    DividendInfo,
    EarningsScheduleEntry,
    TickerCalendar,
)
from stock_screener.timing.infrastructure.calendar_repository import (
    DEFAULT_PATH,
    CalendarRepository,
)


def _make_sample_calendar() -> CalendarData:
    return CalendarData(tickers={
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
    })


class TestCalendarRepository:
    def test_load_returns_empty_when_file_missing(self, tmp_path):
        repo = CalendarRepository(path=tmp_path / "calendar.json")
        cal = repo.load()
        assert len(cal.tickers) == 0

    def test_save_and_load_roundtrip(self, tmp_path):
        path = tmp_path / "calendar.json"
        repo = CalendarRepository(path=path)
        cal = _make_sample_calendar()
        repo.save(cal)

        loaded = repo.load()
        assert len(loaded.tickers) == 1
        assert loaded.tickers["5599.T"].name == "S&J"
        assert loaded.tickers["5599.T"].earnings_schedule[0].next_date == "2026-05-14"
        assert loaded.tickers["5599.T"].dividend.record_date == "2026-03-31"

    def test_save_creates_parent_directory(self, tmp_path):
        path = tmp_path / "nested" / "dir" / "calendar.json"
        repo = CalendarRepository(path=path)
        cal = _make_sample_calendar()
        repo.save(cal)

        loaded = repo.load()
        assert len(loaded.tickers) == 1

    def test_default_path_points_to_project_data_dir(self):
        """DEFAULT_PATH がプロジェクトルートの data/calendar.json を指すこと"""
        assert DEFAULT_PATH.name == "calendar.json"
        assert DEFAULT_PATH.parent.name == "data"
        # data/ の親がプロジェクトルート(pyproject.toml がある)
        project_root = DEFAULT_PATH.parent.parent
        assert (project_root / "pyproject.toml").exists()
