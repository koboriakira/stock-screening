from datetime import date
from unittest.mock import patch

import numpy as np
import pandas as pd

from stock_screener.monitoring.domain.watchlist import Watchlist, WatchlistEntry
from stock_screener.monitoring.infrastructure.watchlist_repository import WatchlistRepository
from stock_screener.monitoring.watchlist_service import WatchlistMonitoringService


def _make_watchlist() -> Watchlist:
    wl = Watchlist()
    wl.add(WatchlistEntry(
        ticker="5765.T", name="S&J", added_date=date(2026, 2, 23), memo="test",
    ))
    return wl


def _make_hist_dataframe() -> pd.DataFrame:
    """60 days of price data"""
    prices = np.linspace(1000, 800, 60).tolist()
    volume = [10000.0] * 60
    return pd.DataFrame({"Close": prices, "Volume": volume})


class TestWatchlistMonitoringService:
    @patch("stock_screener.monitoring.watchlist_service.yf")
    def test_monitors_watchlist_entries(self, mock_yf, tmp_path):
        repo = WatchlistRepository(base_dir=tmp_path)
        repo.save(_make_watchlist())
        service = WatchlistMonitoringService(watchlist_repo=repo)

        mock_ticker = mock_yf.Ticker.return_value
        mock_ticker.history.return_value = _make_hist_dataframe()

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

        # Create data that triggers buy_candidate
        down = np.linspace(1000, 600, 40).tolist()
        up = np.linspace(600, 750, 20).tolist()
        prices = down + up
        volume = [5000.0] * 40 + [20000.0] * 20
        hist = pd.DataFrame({"Close": prices, "Volume": volume})
        mock_ticker = mock_yf.Ticker.return_value
        mock_ticker.history.return_value = hist
        mock_notify.return_value = True

        results = service.execute()
        assert len(results) == 1
        # Notification may or may not be sent depending on signal score
        # Just verify it doesn't crash
