from datetime import date, timedelta

from stock_screener.monitoring.domain.watchlist import (
    ScoreRecord,
    Watchlist,
    WatchlistEntry,
    WatchlistParams,
)
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

    def test_save_and_load_with_new_fields(self, tmp_path):
        repo = WatchlistRepository(base_dir=tmp_path)
        wl = Watchlist()
        wl.add(WatchlistEntry(
            ticker="5765.T",
            name="S&J",
            added_date=date(2026, 2, 23),
            registered_price=1500.0,
            last_notified_at=date(2026, 2, 20),
            params=WatchlistParams(cooldown_days=5),
            score_history=[ScoreRecord(date=date(2026, 2, 22), score=3)],
        ))
        repo.save(wl)

        loaded = repo.load()
        entry = loaded.entries[0]
        assert entry.registered_price == 1500.0
        assert entry.last_notified_at == date(2026, 2, 20)
        assert entry.params.cooldown_days == 5
        assert len(entry.score_history) == 1

    def test_save_trims_score_history_to_90_days(self, tmp_path):
        repo = WatchlistRepository(base_dir=tmp_path)
        wl = Watchlist()
        # 100 日分のスコア履歴を作成
        base_date = date(2026, 2, 23)
        history = [
            ScoreRecord(date=base_date - timedelta(days=i), score=i % 5)
            for i in range(100)
        ]
        wl.add(WatchlistEntry(
            ticker="5765.T",
            name="S&J",
            added_date=date(2026, 1, 1),
            score_history=history,
        ))
        repo.save(wl)

        loaded = repo.load()
        entry = loaded.entries[0]
        assert len(entry.score_history) == 90

    def test_save_keeps_latest_90_records(self, tmp_path):
        repo = WatchlistRepository(base_dir=tmp_path)
        wl = Watchlist()
        base_date = date(2026, 2, 23)
        # 日付順に古い→新しいで作成
        history = [
            ScoreRecord(date=base_date - timedelta(days=99 - i), score=i)
            for i in range(100)
        ]
        wl.add(WatchlistEntry(
            ticker="5765.T",
            name="S&J",
            added_date=date(2026, 1, 1),
            score_history=history,
        ))
        repo.save(wl)

        loaded = repo.load()
        entry = loaded.entries[0]
        # 最新 90 件を保持 (score=10~99)
        assert entry.score_history[0].score == 10
        assert entry.score_history[-1].score == 99

    def test_save_does_not_trim_under_90(self, tmp_path):
        repo = WatchlistRepository(base_dir=tmp_path)
        wl = Watchlist()
        history = [
            ScoreRecord(date=date(2026, 2, i + 1), score=i)
            for i in range(10)
        ]
        wl.add(WatchlistEntry(
            ticker="5765.T",
            name="S&J",
            added_date=date(2026, 1, 1),
            score_history=history,
        ))
        repo.save(wl)

        loaded = repo.load()
        entry = loaded.entries[0]
        assert len(entry.score_history) == 10
