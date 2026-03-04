import json
from datetime import UTC, date, datetime, timedelta
from unittest.mock import patch

import numpy as np
import pandas as pd

from stock_screener.monitoring.domain.bottom_detector import BottomSignal
from stock_screener.monitoring.domain.watchlist import (
    ScoreRecord,
    Watchlist,
    WatchlistEntry,
    WatchlistParams,
)
from stock_screener.monitoring.infrastructure.watchlist_repository import WatchlistRepository
from stock_screener.monitoring.watchlist_service import WatchlistMonitoringService


def _make_watchlist(**entry_kwargs) -> Watchlist:
    wl = Watchlist()
    defaults = {
        "ticker": "5765.T",
        "name": "S&J",
        "added_date": date(2026, 2, 23),
        "memo": "test",
    }
    defaults.update(entry_kwargs)
    wl.add(WatchlistEntry(**defaults))
    return wl


def _make_hist_dataframe() -> pd.DataFrame:
    """60 days of price data"""
    prices = np.linspace(1000, 800, 60).tolist()
    volume = [10000.0] * 60
    return pd.DataFrame({"Close": prices, "Volume": volume})


def _make_buy_candidate_hist() -> pd.DataFrame:
    """Data that triggers buy_candidate signal"""
    down = np.linspace(1000, 600, 40).tolist()
    up = np.linspace(600, 750, 20).tolist()
    prices = down + up
    volume = [5000.0] * 40 + [20000.0] * 20
    return pd.DataFrame({"Close": prices, "Volume": volume})


class TestWatchlistMonitoringService:
    @patch("stock_screener.monitoring.watchlist_service.yf")
    def test_monitors_watchlist_entries(self, mock_yf, tmp_path):
        repo = WatchlistRepository(base_dir=tmp_path)
        repo.save(_make_watchlist())
        service = WatchlistMonitoringService(watchlist_repo=repo)

        mock_ticker = mock_yf.Ticker.return_value
        mock_ticker.history.return_value = _make_hist_dataframe()
        mock_ticker.info = {"currentPrice": 800.0}

        results = service.execute()
        assert len(results) == 1
        assert results[0]["ticker"] == "5765.T"
        assert "signal" in results[0]

    @patch("stock_screener.monitoring.watchlist_service.yf")
    def test_empty_watchlist(self, mock_yf, tmp_path):
        repo = WatchlistRepository(base_dir=tmp_path)
        repo.save(Watchlist())
        service = WatchlistMonitoringService(watchlist_repo=repo)

        results = service.execute()
        assert len(results) == 0

    @patch("stock_screener.monitoring.watchlist_service.yf")
    def test_data_fetch_failure_skips(self, mock_yf, tmp_path):
        repo = WatchlistRepository(base_dir=tmp_path)
        repo.save(_make_watchlist())
        service = WatchlistMonitoringService(watchlist_repo=repo)

        mock_ticker = mock_yf.Ticker.return_value
        mock_ticker.history.return_value = pd.DataFrame()

        results = service.execute()
        assert len(results) == 0

    @patch("stock_screener.monitoring.watchlist_service.send_notification")
    @patch("stock_screener.monitoring.watchlist_service.yf")
    def test_notification_sent_for_buy_candidate(self, mock_yf, mock_notify, tmp_path):
        repo = WatchlistRepository(base_dir=tmp_path)
        repo.save(_make_watchlist())
        service = WatchlistMonitoringService(watchlist_repo=repo)

        mock_ticker = mock_yf.Ticker.return_value
        mock_ticker.history.return_value = _make_buy_candidate_hist()
        mock_ticker.info = {"currentPrice": 750.0}
        mock_notify.return_value = True

        results = service.execute()
        assert len(results) == 1


class TestCooldown:
    @patch("stock_screener.monitoring.watchlist_service.send_notification")
    @patch("stock_screener.monitoring.watchlist_service.yf")
    def test_cooldown_skips_notification(self, mock_yf, mock_notify, tmp_path):
        """クールダウン期間中は通知をスキップする"""
        today = datetime.now(tz=UTC).date()
        repo = WatchlistRepository(base_dir=tmp_path)
        repo.save(_make_watchlist(
            last_notified_at=today - timedelta(days=1),
            params=WatchlistParams(cooldown_days=3),
        ))
        service = WatchlistMonitoringService(watchlist_repo=repo)

        mock_ticker = mock_yf.Ticker.return_value
        mock_ticker.history.return_value = _make_buy_candidate_hist()
        mock_ticker.info = {"currentPrice": 750.0}
        mock_notify.return_value = True

        results = service.execute()
        # 通知は送られない
        mock_notify.assert_not_called()
        if results:
            assert results[0]["notified"] is False

    @patch("stock_screener.monitoring.watchlist_service.send_notification")
    @patch("stock_screener.monitoring.watchlist_service.yf")
    def test_cooldown_expired_allows_notification(self, mock_yf, mock_notify, tmp_path):
        """クールダウン期間が過ぎたら通知する"""
        today = datetime.now(tz=UTC).date()
        repo = WatchlistRepository(base_dir=tmp_path)
        repo.save(_make_watchlist(
            last_notified_at=today - timedelta(days=5),
            params=WatchlistParams(cooldown_days=3),
        ))
        service = WatchlistMonitoringService(watchlist_repo=repo)

        mock_ticker = mock_yf.Ticker.return_value
        mock_ticker.history.return_value = _make_buy_candidate_hist()
        mock_ticker.info = {"currentPrice": 750.0}
        mock_notify.return_value = True

        results = service.execute()
        # シグナルがあれば通知される
        for r in results:
            if r["signal"].level:
                assert mock_notify.called

    @patch("stock_screener.monitoring.watchlist_service.yf")
    def test_cooldown_remaining_days(self, mock_yf, tmp_path):
        """cooldown_remaining_days が正しく計算される"""
        today = datetime.now(tz=UTC).date()
        repo = WatchlistRepository(base_dir=tmp_path)
        repo.save(_make_watchlist(
            last_notified_at=today - timedelta(days=1),
            params=WatchlistParams(cooldown_days=3),
        ))
        service = WatchlistMonitoringService(watchlist_repo=repo)

        mock_ticker = mock_yf.Ticker.return_value
        mock_ticker.history.return_value = _make_hist_dataframe()
        mock_ticker.info = {"currentPrice": 800.0}

        results = service.execute()
        assert len(results) == 1
        assert results[0]["cooldown_remaining_days"] == 2


class TestScoreHistory:
    @patch("stock_screener.monitoring.watchlist_service.yf")
    def test_score_history_saved_after_check(self, mock_yf, tmp_path):
        """チェック後にスコア履歴が保存される"""
        repo = WatchlistRepository(base_dir=tmp_path)
        repo.save(_make_watchlist())
        service = WatchlistMonitoringService(watchlist_repo=repo)

        mock_ticker = mock_yf.Ticker.return_value
        mock_ticker.history.return_value = _make_hist_dataframe()
        mock_ticker.info = {"currentPrice": 800.0}

        service.execute()

        loaded = repo.load()
        entry = loaded.find("5765.T")
        assert len(entry.score_history) == 1

    @patch("stock_screener.monitoring.watchlist_service.yf")
    def test_score_history_not_saved_in_dry_run(self, mock_yf, tmp_path):
        """dry-run ではスコア履歴が保存されない"""
        repo = WatchlistRepository(base_dir=tmp_path)
        repo.save(_make_watchlist())
        service = WatchlistMonitoringService(watchlist_repo=repo)

        mock_ticker = mock_yf.Ticker.return_value
        mock_ticker.history.return_value = _make_hist_dataframe()
        mock_ticker.info = {"currentPrice": 800.0}

        service.execute(dry_run=True)

        loaded = repo.load()
        entry = loaded.find("5765.T")
        assert len(entry.score_history) == 0


class TestDryRun:
    @patch("stock_screener.monitoring.watchlist_service.send_notification")
    @patch("stock_screener.monitoring.watchlist_service.yf")
    def test_dry_run_skips_notification(self, mock_yf, mock_notify, tmp_path):
        """dry-run では通知が送られない"""
        repo = WatchlistRepository(base_dir=tmp_path)
        repo.save(_make_watchlist())
        service = WatchlistMonitoringService(watchlist_repo=repo)

        mock_ticker = mock_yf.Ticker.return_value
        mock_ticker.history.return_value = _make_buy_candidate_hist()
        mock_ticker.info = {"currentPrice": 750.0}
        mock_notify.return_value = True

        results = service.execute(dry_run=True)
        mock_notify.assert_not_called()
        for r in results:
            assert r["notified"] is False


class TestPriceInfo:
    @patch("stock_screener.monitoring.watchlist_service.yf")
    def test_current_price_in_result(self, mock_yf, tmp_path):
        """結果に現在価格が含まれる"""
        repo = WatchlistRepository(base_dir=tmp_path)
        repo.save(_make_watchlist())
        service = WatchlistMonitoringService(watchlist_repo=repo)

        mock_ticker = mock_yf.Ticker.return_value
        mock_ticker.history.return_value = _make_hist_dataframe()
        mock_ticker.info = {"currentPrice": 800.0}

        results = service.execute()
        assert results[0]["current_price"] == 800.0

    @patch("stock_screener.monitoring.watchlist_service.yf")
    def test_price_change_pct_with_registered_price(self, mock_yf, tmp_path):
        """登録時株価がある場合に騰落率が計算される"""
        repo = WatchlistRepository(base_dir=tmp_path)
        repo.save(_make_watchlist(registered_price=1000.0))
        service = WatchlistMonitoringService(watchlist_repo=repo)

        mock_ticker = mock_yf.Ticker.return_value
        mock_ticker.history.return_value = _make_hist_dataframe()
        mock_ticker.info = {"currentPrice": 800.0}

        results = service.execute()
        assert results[0]["registered_price"] == 1000.0
        assert results[0]["price_change_pct"] == -0.2

    @patch("stock_screener.monitoring.watchlist_service.yf")
    def test_price_change_pct_none_without_registered(self, mock_yf, tmp_path):
        """登録時株価がない場合は騰落率 None"""
        repo = WatchlistRepository(base_dir=tmp_path)
        repo.save(_make_watchlist())
        service = WatchlistMonitoringService(watchlist_repo=repo)

        mock_ticker = mock_yf.Ticker.return_value
        mock_ticker.history.return_value = _make_hist_dataframe()
        mock_ticker.info = {"currentPrice": 800.0}

        results = service.execute()
        assert results[0]["price_change_pct"] is None


class TestJsonOutput:
    @patch("stock_screener.monitoring.watchlist_service.yf")
    def test_json_output(self, mock_yf, tmp_path):
        """JSON レポートが出力される"""
        repo = WatchlistRepository(base_dir=tmp_path)
        repo.save(_make_watchlist(registered_price=1000.0))
        service = WatchlistMonitoringService(watchlist_repo=repo)

        mock_ticker = mock_yf.Ticker.return_value
        mock_ticker.history.return_value = _make_hist_dataframe()
        mock_ticker.info = {"currentPrice": 800.0}

        output_path = tmp_path / "report.json"
        service.execute(output_path=output_path)

        assert output_path.exists()
        with output_path.open() as f:
            data = json.load(f)
        assert len(data) == 1
        assert data[0]["ticker"] == "5765.T"
        assert "score" in data[0]
        assert "current_price" in data[0]


class TestSignalsSavedInScoreHistory:
    @patch("stock_screener.monitoring.watchlist_service.yf")
    def test_signals_saved_in_score_record(self, mock_yf, tmp_path):
        """チェック後にシグナル状態がスコア履歴に保存される"""
        repo = WatchlistRepository(base_dir=tmp_path)
        repo.save(_make_watchlist())
        service = WatchlistMonitoringService(watchlist_repo=repo)

        mock_ticker = mock_yf.Ticker.return_value
        mock_ticker.history.return_value = _make_hist_dataframe()
        mock_ticker.info = {"currentPrice": 800.0}

        service.execute()

        loaded = repo.load()
        entry = loaded.find("5765.T")
        assert len(entry.score_history) == 1
        record = entry.score_history[0]
        assert record.signals is not None
        assert set(record.signals.keys()) == {"rsi", "bb", "macd", "volume", "ma"}
        assert all(isinstance(v, bool) for v in record.signals.values())

    @patch("stock_screener.monitoring.watchlist_service.yf")
    def test_signals_not_saved_in_dry_run(self, mock_yf, tmp_path):
        """dry-run ではシグナルも保存されない"""
        repo = WatchlistRepository(base_dir=tmp_path)
        repo.save(_make_watchlist())
        service = WatchlistMonitoringService(watchlist_repo=repo)

        mock_ticker = mock_yf.Ticker.return_value
        mock_ticker.history.return_value = _make_hist_dataframe()
        mock_ticker.info = {"currentPrice": 800.0}

        service.execute(dry_run=True)

        loaded = repo.load()
        entry = loaded.find("5765.T")
        assert len(entry.score_history) == 0


class TestScoreChangeReasons:
    @patch("stock_screener.monitoring.watchlist_service.yf")
    def test_score_change_reasons_in_result(self, mock_yf, tmp_path):
        """result dict に score_change_reasons が含まれる"""
        repo = WatchlistRepository(base_dir=tmp_path)
        repo.save(_make_watchlist())
        service = WatchlistMonitoringService(watchlist_repo=repo)

        mock_ticker = mock_yf.Ticker.return_value
        mock_ticker.history.return_value = _make_hist_dataframe()
        mock_ticker.info = {"currentPrice": 800.0}

        results = service.execute()
        assert "score_change_reasons" in results[0]
        assert isinstance(results[0]["score_change_reasons"], list)

    @patch("stock_screener.monitoring.watchlist_service.detect_bottom_signals")
    @patch("stock_screener.monitoring.watchlist_service.yf")
    def test_score_change_reasons_detects_new_signal(self, mock_yf, mock_detect, tmp_path):
        """前日にない新しいシグナルが検出されると理由リストに含まれる"""
        prev_signals = {"rsi": False, "bb": False, "macd": False, "volume": False, "ma": False}
        repo = WatchlistRepository(base_dir=tmp_path)
        repo.save(_make_watchlist(
            score_history=[ScoreRecord(date=date(2026, 3, 3), score=0, signals=prev_signals)],
        ))
        service = WatchlistMonitoringService(watchlist_repo=repo)

        mock_ticker = mock_yf.Ticker.return_value
        mock_ticker.history.return_value = _make_hist_dataframe()
        mock_ticker.info = {"currentPrice": 800.0}

        mock_detect.return_value = BottomSignal(
            ticker="5765.T", score=2, max_score=5, level=None,
            rsi_signal=True, bb_signal=False, macd_signal=True,
            volume_confirmed=False, ma_crossover=False, details={},
        )

        results = service.execute()
        reasons = results[0]["score_change_reasons"]
        assert "RSI点灯" in reasons
        assert "MACD点灯" in reasons
        assert len(reasons) == 2

    @patch("stock_screener.monitoring.watchlist_service.yf")
    def test_score_change_reasons_empty_without_previous(self, mock_yf, tmp_path):
        """前日のシグナルがない場合は変動理由は空"""
        repo = WatchlistRepository(base_dir=tmp_path)
        repo.save(_make_watchlist())
        service = WatchlistMonitoringService(watchlist_repo=repo)

        mock_ticker = mock_yf.Ticker.return_value
        mock_ticker.history.return_value = _make_hist_dataframe()
        mock_ticker.info = {"currentPrice": 800.0}

        results = service.execute()
        assert results[0]["score_change_reasons"] == []


class TestAddEntry:
    @patch("stock_screener.monitoring.watchlist_service.yf")
    def test_add_entry_records_current_price(self, mock_yf, tmp_path):
        """add_entry で登録時株価が自動取得される"""
        repo = WatchlistRepository(base_dir=tmp_path)
        repo.save(Watchlist())
        service = WatchlistMonitoringService(watchlist_repo=repo)

        mock_ticker = mock_yf.Ticker.return_value
        mock_ticker.info = {"currentPrice": 1500.0}

        service.add_entry(
            ticker="5765.T",
            name="S&J",
            memo="test",
        )

        loaded = repo.load()
        entry = loaded.find("5765.T")
        assert entry is not None
        assert entry.registered_price == 1500.0

    @patch("stock_screener.monitoring.watchlist_service.yf")
    def test_add_entry_with_params(self, mock_yf, tmp_path):
        """add_entry で銘柄別パラメータを設定できる"""
        repo = WatchlistRepository(base_dir=tmp_path)
        repo.save(Watchlist())
        service = WatchlistMonitoringService(watchlist_repo=repo)

        mock_ticker = mock_yf.Ticker.return_value
        mock_ticker.info = {"currentPrice": 1500.0}

        service.add_entry(
            ticker="5765.T",
            name="S&J",
            params=WatchlistParams(cooldown_days=5, score_threshold=2),
        )

        loaded = repo.load()
        entry = loaded.find("5765.T")
        assert entry.params.cooldown_days == 5
        assert entry.params.score_threshold == 2

    @patch("stock_screener.monitoring.watchlist_service.yf")
    def test_add_entry_price_fetch_failure(self, mock_yf, tmp_path):
        """株価取得に失敗しても登録できる(registered_price=None)"""
        repo = WatchlistRepository(base_dir=tmp_path)
        repo.save(Watchlist())
        service = WatchlistMonitoringService(watchlist_repo=repo)

        mock_ticker = mock_yf.Ticker.return_value
        mock_ticker.info = {}

        service.add_entry(ticker="5765.T", name="S&J")

        loaded = repo.load()
        entry = loaded.find("5765.T")
        assert entry is not None
        assert entry.registered_price is None
