from __future__ import annotations

import json
from unittest.mock import patch

import pandas as pd
import pytest
import requests

from stock_screener.cli import main


def _hist_df(rows: list[dict], dates: list[str]) -> pd.DataFrame:
    return pd.DataFrame(rows, index=pd.DatetimeIndex(dates))


def _two_day_bars() -> pd.DataFrame:
    return _hist_df(
        [
            {"Open": 100.0, "High": 110.0, "Low": 95.0, "Close": 105.0, "Volume": 1_000},
            {"Open": 105.0, "High": 115.0, "Low": 100.0, "Close": 112.0, "Volume": 1_200},
        ],
        ["2026-07-10", "2026-07-11"],
    )


class TestCliHistorySingle:
    def test_success_default_period_interval(self, capsys):
        hist = _two_day_bars()
        with (
            patch("sys.argv", ["stock-screener", "history", "7203"]),
            patch("stock_screener.cli.fetch_history", return_value=hist) as mock_fetch,
        ):
            main()
        mock_fetch.assert_called_once_with("7203.T", period="3mo", interval="1d")
        out = json.loads(capsys.readouterr().out)
        assert out["type"] == "history"
        assert out["count"] == 1
        item = out["items"][0]
        assert item["ticker"] == "7203.T"
        assert item["period"] == "3mo"
        assert item["interval"] == "1d"

    def test_custom_period_interval(self, capsys):
        hist = _hist_df([{"Open": 1, "High": 2, "Low": 0.5, "Close": 1.5, "Volume": 10}], ["2026-07-11"])
        with (
            patch("sys.argv", ["stock-screener", "history", "7203", "--period", "1y", "--interval", "1wk"]),
            patch("stock_screener.cli.fetch_history", return_value=hist) as mock_fetch,
        ):
            main()
        mock_fetch.assert_called_once_with("7203.T", period="1y", interval="1wk")
        out = json.loads(capsys.readouterr().out)
        assert out["items"][0]["period"] == "1y"
        assert out["items"][0]["interval"] == "1wk"


class TestCliHistoryBarsShape:
    def test_bars_are_oldest_first_with_all_fields(self, capsys):
        hist = _two_day_bars()
        with (
            patch("sys.argv", ["stock-screener", "history", "7203"]),
            patch("stock_screener.cli.fetch_history", return_value=hist),
        ):
            main()
        out = json.loads(capsys.readouterr().out)
        bars = out["items"][0]["bars"]
        assert len(bars) == 2
        assert bars[0]["date"] == "2026-07-10"
        assert bars[1]["date"] == "2026-07-11"
        assert bars[0] == {
            "date": "2026-07-10",
            "open": 100.0,
            "high": 110.0,
            "low": 95.0,
            "close": 105.0,
            "volume": 1_000,
        }
        assert bars[1]["close"] == 112.0
        assert bars[1]["volume"] == 1_200


class TestCliHistoryMultiple:
    def test_multiple_tickers(self, capsys):
        hist_a = _two_day_bars()
        hist_b = _two_day_bars()
        with (
            patch("sys.argv", ["stock-screener", "history", "7203", "6758"]),
            patch("stock_screener.cli.fetch_history", side_effect=[hist_a, hist_b]),
        ):
            main()
        out = json.loads(capsys.readouterr().out)
        assert out["count"] == 2
        tickers = {item["ticker"] for item in out["items"]}
        assert tickers == {"7203.T", "6758.T"}


class TestCliHistoryInvalidChoices:
    def test_invalid_period_choice_exits_2(self):
        with (
            patch("sys.argv", ["stock-screener", "history", "7203", "--period", "99y"]),
            pytest.raises(SystemExit) as exc_info,
        ):
            main()
        assert exc_info.value.code == 2

    def test_invalid_interval_choice_exits_2(self):
        with (
            patch("sys.argv", ["stock-screener", "history", "7203", "--interval", "1m"]),
            pytest.raises(SystemExit) as exc_info,
        ):
            main()
        assert exc_info.value.code == 2


class TestCliHistoryNoData:
    def test_no_data_is_exit_0_with_errors(self, capsys):
        empty = pd.DataFrame()
        with (
            patch("sys.argv", ["stock-screener", "history", "9999"]),
            patch("stock_screener.cli.fetch_history", return_value=empty),
        ):
            main()
        out = json.loads(capsys.readouterr().out)
        assert out["count"] == 0
        assert out["errors"][0]["ticker"] == "9999.T"
        assert out["errors"][0]["code"] == "no_data"


class TestCliHistoryAllFetchFailed:
    def test_all_fetch_errors_exit_1(self, capsys):
        with (
            patch("sys.argv", ["stock-screener", "history", "7203"]),
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


class TestCliHistoryInvalidTicker:
    def test_invalid_ticker_exits_2_without_fetching(self, capsys):
        with (
            patch("sys.argv", ["stock-screener", "history", "abc"]),
            patch("stock_screener.cli.fetch_history") as mock_fetch,
            pytest.raises(SystemExit) as exc_info,
        ):
            main()
        assert exc_info.value.code == 2
        mock_fetch.assert_not_called()
        out = json.loads(capsys.readouterr().out)
        assert out["error"]["code"] == "invalid_ticker"
