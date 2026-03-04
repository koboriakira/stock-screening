from datetime import date

import pytest

from stock_screener.monitoring.domain.watchlist import (
    ScoreRecord,
    Watchlist,
    WatchlistEntry,
    WatchlistParams,
)


class TestWatchlistParams:
    def test_defaults(self):
        p = WatchlistParams()
        assert p.score_threshold == 3
        assert p.volume_threshold == 1.5
        assert p.cooldown_days == 3

    def test_custom_values(self):
        p = WatchlistParams(score_threshold=2, volume_threshold=2.0, cooldown_days=5)
        assert p.score_threshold == 2
        assert p.volume_threshold == 2.0
        assert p.cooldown_days == 5

    def test_to_dict(self):
        p = WatchlistParams(score_threshold=2)
        d = p.to_dict()
        assert d == {"score_threshold": 2, "volume_threshold": 1.5, "cooldown_days": 3}

    def test_from_dict(self):
        d = {"score_threshold": 4, "volume_threshold": 2.0, "cooldown_days": 7}
        p = WatchlistParams.from_dict(d)
        assert p.score_threshold == 4
        assert p.volume_threshold == 2.0
        assert p.cooldown_days == 7

    def test_from_dict_partial(self):
        p = WatchlistParams.from_dict({"cooldown_days": 10})
        assert p.score_threshold == 3
        assert p.volume_threshold == 1.5
        assert p.cooldown_days == 10

    def test_from_dict_empty(self):
        p = WatchlistParams.from_dict({})
        assert p == WatchlistParams()


class TestScoreRecord:
    def test_create(self):
        r = ScoreRecord(date=date(2026, 2, 23), score=3)
        assert r.date == date(2026, 2, 23)
        assert r.score == 3

    def test_to_dict(self):
        r = ScoreRecord(date=date(2026, 2, 23), score=4)
        assert r.to_dict() == {"date": "2026-02-23", "score": 4}

    def test_from_dict(self):
        r = ScoreRecord.from_dict({"date": "2026-02-23", "score": 4})
        assert r.date == date(2026, 2, 23)
        assert r.score == 4

    def test_signals_default_none(self):
        r = ScoreRecord(date=date(2026, 3, 4), score=2)
        assert r.signals is None

    def test_with_signals(self):
        signals = {"rsi": True, "bb": False, "macd": False, "volume": True, "ma": False}
        r = ScoreRecord(date=date(2026, 3, 4), score=2, signals=signals)
        assert r.signals == signals

    def test_to_dict_with_signals(self):
        signals = {"rsi": True, "bb": False, "macd": False, "volume": True, "ma": False}
        r = ScoreRecord(date=date(2026, 3, 4), score=2, signals=signals)
        d = r.to_dict()
        assert d == {"date": "2026-03-04", "score": 2, "signals": signals}

    def test_to_dict_without_signals(self):
        r = ScoreRecord(date=date(2026, 3, 4), score=2)
        d = r.to_dict()
        assert "signals" not in d

    def test_from_dict_with_signals(self):
        signals = {"rsi": True, "bb": False, "macd": True, "volume": False, "ma": True}
        d = {"date": "2026-03-04", "score": 3, "signals": signals}
        r = ScoreRecord.from_dict(d)
        assert r.signals == signals

    def test_from_dict_backward_compatible(self):
        """signals フィールドがない旧形式からの読み込み"""
        d = {"date": "2026-02-23", "score": 4}
        r = ScoreRecord.from_dict(d)
        assert r.signals is None


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

    def test_new_fields_defaults(self):
        e = WatchlistEntry(
            ticker="5765.T",
            name="S&J",
            added_date=date(2026, 2, 23),
        )
        assert e.registered_price is None
        assert e.last_notified_at is None
        assert e.params == WatchlistParams()
        assert e.score_history == []

    def test_create_with_all_fields(self):
        params = WatchlistParams(score_threshold=2, cooldown_days=5)
        history = [ScoreRecord(date=date(2026, 2, 22), score=2)]
        e = WatchlistEntry(
            ticker="5765.T",
            name="S&J",
            added_date=date(2026, 2, 23),
            memo="test",
            registered_price=1500.0,
            last_notified_at=date(2026, 2, 20),
            params=params,
            score_history=history,
        )
        assert e.registered_price == 1500.0
        assert e.last_notified_at == date(2026, 2, 20)
        assert e.params.score_threshold == 2
        assert len(e.score_history) == 1

    def test_to_dict_roundtrip(self):
        params = WatchlistParams(score_threshold=4, volume_threshold=2.0, cooldown_days=7)
        history = [
            ScoreRecord(date=date(2026, 2, 22), score=2),
            ScoreRecord(date=date(2026, 2, 23), score=3),
        ]
        e = WatchlistEntry(
            ticker="5765.T",
            name="S&J",
            added_date=date(2026, 2, 23),
            memo="test",
            registered_price=1500.0,
            last_notified_at=date(2026, 2, 20),
            params=params,
            score_history=history,
        )
        d = e.to_dict()
        restored = WatchlistEntry.from_dict(d)
        assert restored.ticker == e.ticker
        assert restored.name == e.name
        assert restored.added_date == e.added_date
        assert restored.memo == e.memo
        assert restored.registered_price == e.registered_price
        assert restored.last_notified_at == e.last_notified_at
        assert restored.params == e.params
        assert len(restored.score_history) == 2
        assert restored.score_history[0].score == 2

    def test_from_dict_backward_compatible(self):
        """v1 形式(新フィールドなし)からの読み込み"""
        d = {
            "ticker": "5765.T",
            "name": "S&J",
            "added_date": "2026-02-23",
        }
        e = WatchlistEntry.from_dict(d)
        assert e.memo == ""
        assert e.registered_price is None
        assert e.last_notified_at is None
        assert e.params == WatchlistParams()
        assert e.score_history == []

    def test_to_dict_omits_none_fields(self):
        e = WatchlistEntry(
            ticker="5765.T",
            name="S&J",
            added_date=date(2026, 2, 23),
        )
        d = e.to_dict()
        assert "registered_price" not in d
        assert "last_notified_at" not in d
        assert "score_history" not in d


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
        with pytest.raises(ValueError, match="Already in watchlist"):
            wl.add(entry)

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
        with pytest.raises(ValueError, match="Not in watchlist"):
            wl.remove("9999.T")

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

    def test_update_entry(self):
        wl = Watchlist()
        wl.add(WatchlistEntry(
            ticker="5765.T", name="S&J", added_date=date(2026, 2, 23),
        ))
        updated_wl = wl.update_entry("5765.T", registered_price=1500.0, last_notified_at=date(2026, 2, 23))
        # 元の watchlist は変更されない(frozen entry だが Watchlist はmutable、新エントリで差し替え)
        found = updated_wl.find("5765.T")
        assert found is not None
        assert found.registered_price == 1500.0
        assert found.last_notified_at == date(2026, 2, 23)

    def test_update_entry_score_history(self):
        wl = Watchlist()
        wl.add(WatchlistEntry(
            ticker="5765.T", name="S&J", added_date=date(2026, 2, 23),
        ))
        new_history = [ScoreRecord(date=date(2026, 2, 23), score=3)]
        updated_wl = wl.update_entry("5765.T", score_history=new_history)
        found = updated_wl.find("5765.T")
        assert len(found.score_history) == 1

    def test_update_entry_not_found_raises(self):
        wl = Watchlist()
        with pytest.raises(ValueError, match="Not in watchlist"):
            wl.update_entry("9999.T", registered_price=100.0)
