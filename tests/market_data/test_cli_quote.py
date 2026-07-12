from __future__ import annotations

import json
from unittest.mock import patch

import pandas as pd
import pytest
import requests

from stock_screener.cli import main


def _hist_df(rows: list[dict], dates: list[str]) -> pd.DataFrame:
    return pd.DataFrame(rows, index=pd.DatetimeIndex(dates))


def _two_day_hist(close: float = 1500.0, prev_close: float = 1400.0, volume: int = 100_000) -> pd.DataFrame:
    return _hist_df(
        [
            {"Close": prev_close, "Volume": volume - 1000},
            {"Close": close, "Volume": volume},
        ],
        ["2026-07-10", "2026-07-11"],
    )


def _one_day_hist(close: float = 1500.0, volume: int = 100_000) -> pd.DataFrame:
    return _hist_df([{"Close": close, "Volume": volume}], ["2026-07-11"])


class TestCliQuoteSingle:
    def test_success(self, capsys):
        hist = _two_day_hist()
        with (
            patch("sys.argv", ["stock-screener", "quote", "7203"]),
            patch("stock_screener.cli.fetch_history", return_value=hist),
        ):
            main()
        out = json.loads(capsys.readouterr().out)
        assert out["type"] == "quote"
        assert out["count"] == 1
        item = out["items"][0]
        assert item["ticker"] == "7203.T"
        assert item["price"] == 1500.0
        assert item["prev_close"] == 1400.0
        assert item["change_pct"] == pytest.approx(7.14, abs=0.01)
        assert item["volume"] == 100_000
        assert item["date"] == "2026-07-11"


class TestCliQuoteMultiple:
    def test_multiple_tickers(self, capsys):
        hist_a = _two_day_hist(close=1500.0, prev_close=1400.0)
        hist_b = _two_day_hist(close=800.0, prev_close=820.0)
        with (
            patch("sys.argv", ["stock-screener", "quote", "7203", "6758"]),
            patch("stock_screener.cli.fetch_history", side_effect=[hist_a, hist_b]),
        ):
            main()
        out = json.loads(capsys.readouterr().out)
        assert out["count"] == 2
        tickers = {item["ticker"] for item in out["items"]}
        assert tickers == {"7203.T", "6758.T"}


class TestCliQuotePartialFailure:
    def test_no_data_goes_to_errors(self, capsys):
        hist = _two_day_hist()
        empty = pd.DataFrame()
        with (
            patch("sys.argv", ["stock-screener", "quote", "7203", "9999"]),
            patch("stock_screener.cli.fetch_history", side_effect=[hist, empty]),
        ):
            main()
        out = json.loads(capsys.readouterr().out)
        assert out["count"] == 1
        assert len(out["errors"]) == 1
        assert out["errors"][0]["ticker"] == "9999.T"
        assert out["errors"][0]["code"] == "no_data"


class TestCliQuoteAllNoData:
    def test_all_no_data_is_exit_0(self, capsys):
        empty = pd.DataFrame()
        with (
            patch("sys.argv", ["stock-screener", "quote", "7203", "9999"]),
            patch("stock_screener.cli.fetch_history", return_value=empty),
        ):
            main()
        out = json.loads(capsys.readouterr().out)
        assert out["count"] == 0
        assert len(out["errors"]) == 2
        assert {e["code"] for e in out["errors"]} == {"no_data"}


class TestCliQuoteInvalidTicker:
    def test_invalid_ticker_exits_2_without_fetching(self, capsys):
        with (
            patch("sys.argv", ["stock-screener", "quote", "abc"]),
            patch("stock_screener.cli.fetch_history") as mock_fetch,
            pytest.raises(SystemExit) as exc_info,
        ):
            main()
        assert exc_info.value.code == 2
        mock_fetch.assert_not_called()
        out = json.loads(capsys.readouterr().out)
        assert out["type"] == "error"
        assert out["error"]["code"] == "invalid_ticker"

    def test_invalid_ticker_among_valid_ones_fetches_nothing(self, capsys):
        with (
            patch("sys.argv", ["stock-screener", "quote", "7203", "abc"]),
            patch("stock_screener.cli.fetch_history") as mock_fetch,
            pytest.raises(SystemExit) as exc_info,
        ):
            main()
        assert exc_info.value.code == 2
        mock_fetch.assert_not_called()


class TestCliQuoteAllFetchFailed:
    def test_all_fetch_errors_exit_1(self, capsys):
        with (
            patch("sys.argv", ["stock-screener", "quote", "7203"]),
            patch(
                "stock_screener.cli.fetch_history",
                side_effect=requests.exceptions.ConnectionError("timeout"),
            ),
            pytest.raises(SystemExit) as exc_info,
        ):
            main()
        assert exc_info.value.code == 1
        out = json.loads(capsys.readouterr().out)
        assert out["type"] == "error"


class TestCliQuoteSingleBar:
    def test_prev_close_and_change_pct_null_when_single_row(self, capsys):
        hist = _one_day_hist()
        with (
            patch("sys.argv", ["stock-screener", "quote", "7203"]),
            patch("stock_screener.cli.fetch_history", return_value=hist),
        ):
            main()
        out = json.loads(capsys.readouterr().out)
        item = out["items"][0]
        assert item["prev_close"] is None
        assert item["change_pct"] is None
