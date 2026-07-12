from __future__ import annotations

import json
from unittest.mock import patch

import pytest
import requests

from stock_screener.cli import main
from stock_screener.market_data.domain.financial_snapshot import FinancialSnapshot
from stock_screener.market_data.service import SnapshotFetchResult


def _result(snapshot: FinancialSnapshot, cache_hit: bool = False) -> SnapshotFetchResult:
    return SnapshotFetchResult(snapshot=snapshot, cache_hit=cache_hit)


class TestCliFinancialsSingle:
    def test_success(self, capsys):
        snapshot = FinancialSnapshot(market_cap=1_000_000_000, per=12.5, pbr=0.9)
        with (
            patch("sys.argv", ["stock-screener", "financials", "7203"]),
            patch("stock_screener.cli.FinancialSnapshotService") as mock_service_cls,
        ):
            mock_service_cls.return_value.fetch.return_value = _result(snapshot, cache_hit=True)
            main()
        out = json.loads(capsys.readouterr().out)
        assert out["type"] == "financials"
        assert out["count"] == 1
        item = out["items"][0]
        assert item["ticker"] == "7203.T"
        assert item["per"] == 12.5
        assert item["pbr"] == 0.9
        assert item["market_cap"] == 1_000_000_000
        assert item["cache_hit"] is True
        assert item["data_completeness"] == snapshot.data_completeness
        assert out["cache_hit"] is True


class TestCliFinancialsMultiple:
    def test_cache_hit_aggregation_true_only_when_all_hit(self, capsys):
        snap_a = FinancialSnapshot(per=10.0, market_cap=1)
        snap_b = FinancialSnapshot(per=20.0, market_cap=2)
        with (
            patch("sys.argv", ["stock-screener", "financials", "7203", "6758"]),
            patch("stock_screener.cli.FinancialSnapshotService") as mock_service_cls,
        ):
            mock_service_cls.return_value.fetch.side_effect = [
                _result(snap_a, cache_hit=True),
                _result(snap_b, cache_hit=False),
            ]
            main()
        out = json.loads(capsys.readouterr().out)
        assert out["count"] == 2
        assert out["cache_hit"] is False
        tickers = {item["ticker"] for item in out["items"]}
        assert tickers == {"7203.T", "6758.T"}


class TestCliFinancialsNoData:
    def test_empty_snapshot_goes_to_errors(self, capsys):
        with (
            patch("sys.argv", ["stock-screener", "financials", "9999"]),
            patch("stock_screener.cli.FinancialSnapshotService") as mock_service_cls,
        ):
            mock_service_cls.return_value.fetch.return_value = _result(FinancialSnapshot(), cache_hit=False)
            main()
        out = json.loads(capsys.readouterr().out)
        assert out["count"] == 0
        assert len(out["errors"]) == 1
        assert out["errors"][0]["ticker"] == "9999.T"
        assert out["errors"][0]["code"] == "no_data"
        assert out["cache_hit"] is False


class TestCliFinancialsPartialFailure:
    def test_no_data_mixed_with_success(self, capsys):
        snapshot = FinancialSnapshot(per=10.0, market_cap=1)
        with (
            patch("sys.argv", ["stock-screener", "financials", "7203", "9999"]),
            patch("stock_screener.cli.FinancialSnapshotService") as mock_service_cls,
        ):
            mock_service_cls.return_value.fetch.side_effect = [
                _result(snapshot, cache_hit=False),
                _result(FinancialSnapshot(), cache_hit=False),
            ]
            main()
        out = json.loads(capsys.readouterr().out)
        assert out["count"] == 1
        assert len(out["errors"]) == 1
        assert out["errors"][0]["ticker"] == "9999.T"
        assert out["errors"][0]["code"] == "no_data"


class TestCliFinancialsInvalidTicker:
    def test_invalid_ticker_exits_2_without_fetching(self, capsys):
        with (
            patch("sys.argv", ["stock-screener", "financials", "abc"]),
            patch("stock_screener.cli.FinancialSnapshotService") as mock_service_cls,
            pytest.raises(SystemExit) as exc_info,
        ):
            main()
        assert exc_info.value.code == 2
        mock_service_cls.return_value.fetch.assert_not_called()
        out = json.loads(capsys.readouterr().out)
        assert out["type"] == "error"
        assert out["error"]["code"] == "invalid_ticker"

    def test_invalid_ticker_among_valid_ones_fetches_nothing(self, capsys):
        with (
            patch("sys.argv", ["stock-screener", "financials", "7203", "abc"]),
            patch("stock_screener.cli.FinancialSnapshotService") as mock_service_cls,
            pytest.raises(SystemExit) as exc_info,
        ):
            main()
        assert exc_info.value.code == 2
        mock_service_cls.return_value.fetch.assert_not_called()


class TestCliFinancialsAllFetchFailed:
    def test_all_fetch_errors_exit_1(self, capsys):
        with (
            patch("sys.argv", ["stock-screener", "financials", "7203"]),
            patch("stock_screener.cli.FinancialSnapshotService") as mock_service_cls,
        ):
            mock_service_cls.return_value.fetch.side_effect = requests.exceptions.ConnectionError("timeout")
            with pytest.raises(SystemExit) as exc_info:
                main()
        assert exc_info.value.code == 1
        out = json.loads(capsys.readouterr().out)
        assert out["type"] == "error"


class TestCliFinancialsNoCacheFlag:
    def test_no_cache_flag_constructs_service_with_none(self, capsys):
        snapshot = FinancialSnapshot(per=10.0, market_cap=1)
        with (
            patch("sys.argv", ["stock-screener", "financials", "7203", "--no-cache"]),
            patch("stock_screener.cli.FinancialSnapshotService") as mock_service_cls,
        ):
            mock_service_cls.return_value.fetch.return_value = _result(snapshot, cache_hit=False)
            main()
        mock_service_cls.assert_called_once_with(cache=None)

    def test_default_constructs_service_with_filecache(self, capsys):
        snapshot = FinancialSnapshot(per=10.0, market_cap=1)
        with (
            patch("sys.argv", ["stock-screener", "financials", "7203"]),
            patch("stock_screener.cli.FinancialSnapshotService") as mock_service_cls,
            patch("stock_screener.cli.FileCache") as mock_cache_cls,
        ):
            mock_service_cls.return_value.fetch.return_value = _result(snapshot, cache_hit=False)
            main()
        mock_service_cls.assert_called_once_with(cache=mock_cache_cls.return_value)
