from datetime import date

from stock_screener.monitoring.domain.watchlist import Watchlist, WatchlistEntry


class TestWatchlistEntry:
    def test_create_entry(self):
        e = WatchlistEntry(
            ticker="5765.T",
            name="S&J",
            added_date=date(2026, 2, 23),
            memo="値下げトレンド監視",
        )
        assert e.ticker == "5765.T"
        assert e.name == "S&J"
        assert e.added_date == date(2026, 2, 23)
        assert e.memo == "値下げトレンド監視"

    def test_default_memo_is_empty(self):
        e = WatchlistEntry(
            ticker="5765.T",
            name="S&J",
            added_date=date(2026, 2, 23),
        )
        assert e.memo == ""

    def test_to_dict_roundtrip(self):
        e = WatchlistEntry(
            ticker="5765.T",
            name="S&J",
            added_date=date(2026, 2, 23),
            memo="test",
        )
        d = e.to_dict()
        restored = WatchlistEntry.from_dict(d)
        assert restored.ticker == e.ticker
        assert restored.name == e.name
        assert restored.added_date == e.added_date
        assert restored.memo == e.memo

    def test_from_dict_backward_compatible(self):
        d = {
            "ticker": "5765.T",
            "name": "S&J",
            "added_date": "2026-02-23",
        }
        e = WatchlistEntry.from_dict(d)
        assert e.memo == ""


class TestWatchlist:
    def test_create_empty(self):
        wl = Watchlist()
        assert len(wl.entries) == 0

    def test_add_entry(self):
        wl = Watchlist()
        entry = WatchlistEntry(
            ticker="5765.T", name="S&J", added_date=date(2026, 2, 23),
        )
        wl.add(entry)
        assert len(wl.entries) == 1

    def test_add_duplicate_raises(self):
        wl = Watchlist()
        entry = WatchlistEntry(
            ticker="5765.T", name="S&J", added_date=date(2026, 2, 23),
        )
        wl.add(entry)
        try:
            wl.add(entry)
            msg = "Expected ValueError"
            raise AssertionError(msg)
        except ValueError:
            pass

    def test_remove_entry(self):
        wl = Watchlist()
        entry = WatchlistEntry(
            ticker="5765.T", name="S&J", added_date=date(2026, 2, 23),
        )
        wl.add(entry)
        wl.remove("5765.T")
        assert len(wl.entries) == 0

    def test_remove_nonexistent_raises(self):
        wl = Watchlist()
        try:
            wl.remove("9999.T")
            msg = "Expected ValueError"
            raise AssertionError(msg)
        except ValueError:
            pass

    def test_find(self):
        wl = Watchlist()
        entry = WatchlistEntry(
            ticker="5765.T", name="S&J", added_date=date(2026, 2, 23),
        )
        wl.add(entry)
        found = wl.find("5765.T")
        assert found is not None
        assert found.ticker == "5765.T"

    def test_find_not_found(self):
        wl = Watchlist()
        assert wl.find("9999.T") is None

    def test_to_dict_roundtrip(self):
        wl = Watchlist()
        wl.add(WatchlistEntry(
            ticker="5765.T", name="S&J", added_date=date(2026, 2, 23), memo="test",
        ))
        wl.add(WatchlistEntry(
            ticker="1234.T", name="Test", added_date=date(2026, 2, 24),
        ))
        d = wl.to_dict()
        restored = Watchlist.from_dict(d)
        assert len(restored.entries) == 2
        assert restored.find("5765.T") is not None
