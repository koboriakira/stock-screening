from __future__ import annotations

import json
from unittest.mock import patch

import pandas as pd
import pytest
import requests

from stock_screener.cli import main


def _hist_df(rows: list[dict], dates: list[str]) -> pd.DataFrame:
    return pd.DataFrame(rows, index=pd.DatetimeIndex(dates))


def _two_day_hist(close: float, prev_close: float, volume: int = 1_000_000) -> pd.DataFrame:
    return _hist_df(
        [
            {"Close": prev_close, "Volume": volume},
            {"Close": close, "Volume": volume},
        ],
        ["2026-07-16", "2026-07-17"],
    )


def _one_day_hist(close: float = 5000.0) -> pd.DataFrame:
    return _hist_df([{"Close": close, "Volume": 1_000_000}], ["2026-07-17"])


class TestCliUsIndexSuccess:
    def test_returns_both_indices(self, capsys):
        sp500_hist = _two_day_hist(close=5000.0, prev_close=4950.0)
        nasdaq_hist = _two_day_hist(close=16000.0, prev_close=15900.0)
        with (
            patch("sys.argv", ["stock-screener", "us-index"]),
            patch("stock_screener.cli.fetch_history", side_effect=[sp500_hist, nasdaq_hist]),
        ):
            main()
        out = json.loads(capsys.readouterr().out)
        assert out["type"] == "us-index"
        assert out["count"] == 2
        assert out["source"] == "yfinance"
        labels = {item["label"] for item in out["items"]}
        assert labels == {"sp500", "nasdaq"}
        symbols = {item["symbol"] for item in out["items"]}
        assert symbols == {"^GSPC", "^IXIC"}

        sp500_item = next(item for item in out["items"] if item["label"] == "sp500")
        assert sp500_item["symbol"] == "^GSPC"
        assert sp500_item["price"] == 5000.0
        assert sp500_item["prev_close"] == 4950.0
        assert sp500_item["change_pct"] == pytest.approx(1.01, abs=0.01)
        assert sp500_item["date"] == "2026-07-17"


class TestCliUsIndexGapDownAlert:
    def test_gap_down_alert_true_when_below_threshold(self, capsys):
        # change_pct = (4900/4950 - 1) * 100 ~= -1.01% <= -1.0 threshold
        hist = _two_day_hist(close=4900.0, prev_close=4950.0)
        with (
            patch("sys.argv", ["stock-screener", "us-index"]),
            patch("stock_screener.cli.fetch_history", side_effect=[hist, hist]),
        ):
            main()
        out = json.loads(capsys.readouterr().out)
        assert out["count"] == 2
        for item in out["items"]:
            assert item["gap_down_alert"] is True

    def test_gap_down_alert_false_when_above_threshold(self, capsys):
        # change_pct = (4970/4950 - 1) * 100 ~= 0.4% > -1.0 threshold
        hist = _two_day_hist(close=4970.0, prev_close=4950.0)
        with (
            patch("sys.argv", ["stock-screener", "us-index"]),
            patch("stock_screener.cli.fetch_history", side_effect=[hist, hist]),
        ):
            main()
        out = json.loads(capsys.readouterr().out)
        for item in out["items"]:
            assert item["gap_down_alert"] is False


class TestCliUsIndexSingleBar:
    def test_prev_close_and_change_pct_null_when_single_row(self, capsys):
        hist = _one_day_hist()
        with (
            patch("sys.argv", ["stock-screener", "us-index"]),
            patch("stock_screener.cli.fetch_history", side_effect=[hist, hist]),
        ):
            main()
        out = json.loads(capsys.readouterr().out)
        for item in out["items"]:
            assert item["prev_close"] is None
            assert item["change_pct"] is None
            assert item["gap_down_alert"] is False


class TestCliUsIndexPartialFailure:
    def test_one_index_fails_goes_to_errors(self, capsys):
        hist = _two_day_hist(close=5000.0, prev_close=4950.0)
        empty = pd.DataFrame()
        with (
            patch("sys.argv", ["stock-screener", "us-index"]),
            patch("stock_screener.cli.fetch_history", side_effect=[hist, empty]),
        ):
            main()
        out = json.loads(capsys.readouterr().out)
        assert out["count"] == 1
        assert len(out["errors"]) == 1
        assert out["errors"][0]["ticker"] == "^IXIC"
        assert out["errors"][0]["code"] == "no_data"


class TestCliUsIndexAllFailed:
    def test_all_fetch_errors_exit_1(self, capsys):
        with (
            patch("sys.argv", ["stock-screener", "us-index"]),
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


class TestCliUsIndexNoArguments:
    def test_takes_no_period_argument(self, capsys):
        with (
            patch("sys.argv", ["stock-screener", "us-index", "--period", "5d"]),
            pytest.raises(SystemExit) as exc_info,
        ):
            main()
        assert exc_info.value.code == 2
