from datetime import date

from stock_screener.monitoring.domain.watchlist import Watchlist, WatchlistEntry
from stock_screener.monitoring.infrastructure.watchlist_repository import WatchlistRepository


class TestWatchlistRepository:
    def test_load_empty(self, tmp_path):
        repo = WatchlistRepository(base_dir=tmp_path)
        wl = repo.load()
        assert len(wl.entries) == 0

    def test_save_and_load(self, tmp_path):
        repo = WatchlistRepository(base_dir=tmp_path)
        wl = Watchlist()
        wl.add(WatchlistEntry(
            ticker="5765.T", name="S&J", added_date=date(2026, 2, 23), memo="test",
        ))
        repo.save(wl)

        loaded = repo.load()
        assert len(loaded.entries) == 1
        assert loaded.entries[0].ticker == "5765.T"
        assert loaded.entries[0].memo == "test"
