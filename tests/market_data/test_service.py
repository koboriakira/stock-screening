from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd
import requests

from stock_screener.market_data.domain.financial_snapshot import FinancialSnapshot
from stock_screener.market_data.infrastructure.cache import FileCache
from stock_screener.market_data.service import FinancialSnapshotService, rank_decliners
from stock_screener.shared.types import Ticker


def _hist(prev_close: float, close: float, volume: int = 1000) -> pd.DataFrame:
    return pd.DataFrame(
        [{"Close": prev_close, "Volume": volume}, {"Close": close, "Volume": volume}],
        index=pd.DatetimeIndex(["2026-07-16", "2026-07-17"]),
    )


def _universe(n: int) -> list[dict]:
    return [
        {"ticker": str(1000 + i), "company_name": f"会社{i}", "sector": "test", "market": "プライム"} for i in range(n)
    ]


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


class TestRankDeclinersSortOrder:
    def test_sorted_descending_by_decline(self):
        universe = _universe(3)
        # 0: -1%, 1: -5%, 2: +2%
        hist_map = {
            "1000.T": _hist(prev_close=100, close=99),
            "1001.T": _hist(prev_close=100, close=95),
            "1002.T": _hist(prev_close=100, close=102),
        }
        candidates, errors = rank_decliners(universe, top_n=10, fetch=lambda t: hist_map[t])

        assert errors == []
        assert [c.ticker for c in candidates] == ["1001.T", "1000.T", "1002.T"]
        assert candidates[0].change_pct == -5.0
        assert candidates[1].change_pct == -1.0
        assert candidates[2].change_pct == 2.0


class TestRankDeclinersTopNTruncation:
    def test_truncates_to_top_n(self):
        universe = _universe(5)
        hist_map = {f"{1000 + i}.T": _hist(prev_close=100, close=100 - i) for i in range(5)}
        candidates, errors = rank_decliners(universe, top_n=2, fetch=lambda t: hist_map[t])

        assert errors == []
        assert len(candidates) == 2
        # Largest decline (i=4 -> -4%) first
        assert candidates[0].ticker == "1004.T"
        assert candidates[1].ticker == "1003.T"


class TestRankDeclinersFetchFailure:
    def test_fetch_exception_goes_to_errors_and_is_skipped(self):
        universe = _universe(2)

        def fetch(ticker: str) -> pd.DataFrame:
            if ticker == "1000.T":
                message = "boom"
                raise requests.exceptions.ConnectionError(message)
            return _hist(prev_close=100, close=90)

        candidates, errors = rank_decliners(universe, top_n=10, fetch=fetch)

        assert len(candidates) == 1
        assert candidates[0].ticker == "1001.T"
        assert len(errors) == 1
        assert errors[0]["ticker"] == "1000.T"
        assert errors[0]["code"] == "network_error"

    def test_empty_history_goes_to_errors(self):
        universe = _universe(1)
        candidates, errors = rank_decliners(universe, top_n=10, fetch=lambda _t: pd.DataFrame())

        assert candidates == []
        assert len(errors) == 1
        assert errors[0]["code"] == "no_data"


class TestRankDeclinersProgressCallback:
    def test_progress_cb_called_with_index_and_total(self):
        universe = _universe(3)
        calls = []
        rank_decliners(
            universe,
            top_n=10,
            fetch=lambda _t: _hist(prev_close=100, close=99),
            progress_cb=lambda current, total: calls.append((current, total)),
        )
        assert calls == [(1, 3), (2, 3), (3, 3)]
