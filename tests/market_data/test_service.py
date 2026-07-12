from __future__ import annotations

from unittest.mock import MagicMock, patch

from stock_screener.market_data.domain.financial_snapshot import FinancialSnapshot
from stock_screener.market_data.infrastructure.cache import FileCache
from stock_screener.market_data.service import FinancialSnapshotService
from stock_screener.shared.types import Ticker


class TestFinancialSnapshotServiceCacheHit:
    def test_cache_hit_when_key_present(self):
        mock_cache = MagicMock(spec=FileCache)
        mock_cache.get.return_value = {"per": 10.0}
        snapshot = FinancialSnapshot(per=10.0)
        with patch("stock_screener.market_data.service.YFinanceSecurityRepository") as mock_repo_cls:
            mock_repo_cls.return_value.get_financial_snapshot.return_value = snapshot
            service = FinancialSnapshotService(cache=mock_cache)
            result = service.fetch(Ticker("7203"))

        assert result.cache_hit is True
        assert result.snapshot == snapshot
        mock_cache.get.assert_called_once_with("snapshot_7203.T")


class TestFinancialSnapshotServiceCacheMiss:
    def test_cache_miss_when_key_absent(self):
        mock_cache = MagicMock(spec=FileCache)
        mock_cache.get.return_value = None
        snapshot = FinancialSnapshot(per=10.0)
        with patch("stock_screener.market_data.service.YFinanceSecurityRepository") as mock_repo_cls:
            mock_repo_cls.return_value.get_financial_snapshot.return_value = snapshot
            service = FinancialSnapshotService(cache=mock_cache)
            result = service.fetch(Ticker("7203"))

        assert result.cache_hit is False
        assert result.snapshot == snapshot


class TestFinancialSnapshotServiceNoCache:
    def test_no_cache_skips_check_and_reports_miss(self):
        snapshot = FinancialSnapshot(per=10.0)
        with patch("stock_screener.market_data.service.YFinanceSecurityRepository") as mock_repo_cls:
            mock_repo_cls.return_value.get_financial_snapshot.return_value = snapshot
            service = FinancialSnapshotService(cache=None)
            result = service.fetch(Ticker("7203"))

        assert result.cache_hit is False
        mock_repo_cls.assert_called_once_with(cache=None)

    def test_no_cache_does_not_touch_filecache(self):
        snapshot = FinancialSnapshot(per=10.0)
        with (
            patch("stock_screener.market_data.service.YFinanceSecurityRepository") as mock_repo_cls,
            patch("stock_screener.market_data.service.FileCache") as mock_cache_cls,
        ):
            mock_repo_cls.return_value.get_financial_snapshot.return_value = snapshot
            service = FinancialSnapshotService(cache=None)
            service.fetch(Ticker("7203"))

        mock_cache_cls.assert_not_called()


class TestFinancialSnapshotServiceDelegatesFetch:
    def test_repository_is_constructed_with_given_cache(self):
        mock_cache = MagicMock(spec=FileCache)
        mock_cache.get.return_value = None
        snapshot = FinancialSnapshot()
        with patch("stock_screener.market_data.service.YFinanceSecurityRepository") as mock_repo_cls:
            mock_repo_cls.return_value.get_financial_snapshot.return_value = snapshot
            service = FinancialSnapshotService(cache=mock_cache)
            service.fetch(Ticker("7203"))

        mock_repo_cls.assert_called_once_with(cache=mock_cache)
        mock_repo_cls.return_value.get_financial_snapshot.assert_called_once_with(Ticker("7203"))
