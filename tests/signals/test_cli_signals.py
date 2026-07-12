from __future__ import annotations

import json
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest
import requests

from stock_screener.cli import main


def _make_history(close: list[float], volume: list[float] | None = None) -> pd.DataFrame:
    n = len(close)
    if volume is None:
        volume = [10000.0] * n
    return pd.DataFrame({"Close": close, "Volume": volume})


def _make_downtrend_then_recovery() -> pd.DataFrame:
    """60 days: 40 days down from 1000 to 700, then 20 days recovery to 800 (volume spike on recovery)"""
    down = np.linspace(1000, 700, 40).tolist()
    up = np.linspace(700, 800, 20).tolist()
    prices = down + up
    vol = [5000.0] * 40 + [15000.0] * 20
    return _make_history(prices, vol)


class TestCliSignalsSingle:
    def test_success(self, capsys):
        hist = _make_downtrend_then_recovery()
        with (
            patch("sys.argv", ["stock-screener", "signals", "7203"]),
            patch("stock_screener.cli.fetch_history", return_value=hist) as mock_fetch,
        ):
            main()
        mock_fetch.assert_called_once_with("7203.T", period="6mo", interval="1d")
        out = json.loads(capsys.readouterr().out)
        assert out["type"] == "signals"
        assert out["count"] == 1
        item = out["items"][0]
        assert item["ticker"] == "7203.T"
        assert set(item.keys()) == {
            "ticker",
            "score",
            "max_score",
            "level",
            "rsi_signal",
            "bb_signal",
            "macd_signal",
            "volume_confirmed",
            "ma_crossover",
            "details",
            "score_delta",
        }
        assert item["max_score"] == 5
        assert item["score_delta"] is None


class TestCliSignalsMultiple:
    def test_multiple_tickers(self, capsys):
        hist_a = _make_downtrend_then_recovery()
        hist_b = _make_downtrend_then_recovery()
        with (
            patch("sys.argv", ["stock-screener", "signals", "7203", "6758"]),
            patch("stock_screener.cli.fetch_history", side_effect=[hist_a, hist_b]),
        ):
            main()
        out = json.loads(capsys.readouterr().out)
        assert out["count"] == 2
        tickers = {item["ticker"] for item in out["items"]}
        assert tickers == {"7203.T", "6758.T"}


class TestCliSignalsInsufficientData:
    def test_insufficient_data_is_normal_item_not_error(self, capsys):
        """30本未満のデータは bottom_detector の既定挙動どおり score 0 の正常 item を返す"""
        hist = _make_history([100.0, 101.0, 102.0])
        with (
            patch("sys.argv", ["stock-screener", "signals", "7203"]),
            patch("stock_screener.cli.fetch_history", return_value=hist),
        ):
            main()
        out = json.loads(capsys.readouterr().out)
        assert out["count"] == 1
        assert "errors" not in out
        item = out["items"][0]
        assert item["score"] == 0
        assert item["level"] is None


class TestCliSignalsNoData:
    def test_empty_history_goes_to_errors(self, capsys):
        empty = pd.DataFrame()
        with (
            patch("sys.argv", ["stock-screener", "signals", "9999"]),
            patch("stock_screener.cli.fetch_history", return_value=empty),
        ):
            main()
        out = json.loads(capsys.readouterr().out)
        assert out["count"] == 0
        assert len(out["errors"]) == 1
        assert out["errors"][0]["ticker"] == "9999.T"
        assert out["errors"][0]["code"] == "no_data"

    def test_no_data_mixed_with_success_is_exit_0(self, capsys):
        hist = _make_downtrend_then_recovery()
        empty = pd.DataFrame()
        with (
            patch("sys.argv", ["stock-screener", "signals", "7203", "9999"]),
            patch("stock_screener.cli.fetch_history", side_effect=[hist, empty]),
        ):
            main()
        out = json.loads(capsys.readouterr().out)
        assert out["count"] == 1
        assert len(out["errors"]) == 1
        assert out["errors"][0]["ticker"] == "9999.T"


class TestCliSignalsInvalidTicker:
    def test_invalid_ticker_exits_2_without_fetching(self, capsys):
        with (
            patch("sys.argv", ["stock-screener", "signals", "abc"]),
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
            patch("sys.argv", ["stock-screener", "signals", "7203", "abc"]),
            patch("stock_screener.cli.fetch_history") as mock_fetch,
            pytest.raises(SystemExit) as exc_info,
        ):
            main()
        assert exc_info.value.code == 2
        mock_fetch.assert_not_called()


class TestCliSignalsAllFetchFailed:
    def test_all_fetch_errors_exit_1(self, capsys):
        with (
            patch("sys.argv", ["stock-screener", "signals", "7203"]),
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


def _make_downtrend_then_recovery_with_volume_spike() -> pd.DataFrame:
    """60 days: 40 days down, 20 days recovery, with a volume spike on the final day only

    calc_volume_ratio は直近5日平均に対する最終日の比率のため、
    出来高上昇が数日継続するデータでは ratio が 1.0 付近になる。
    最終日だけ急増させることで閾値判定を明確にテストできる。
    """
    down = np.linspace(1000, 700, 40).tolist()
    up = np.linspace(700, 800, 20).tolist()
    prices = down + up
    vol = [5000.0] * 59 + [20000.0]
    return _make_history(prices, vol)


class TestCliSignalsVolumeThreshold:
    def test_volume_threshold_flag_propagates(self, capsys):
        hist = _make_downtrend_then_recovery_with_volume_spike()
        with (
            patch("sys.argv", ["stock-screener", "signals", "7203", "--volume-threshold", "100.0"]),
            patch("stock_screener.cli.fetch_history", return_value=hist),
        ):
            main()
        out = json.loads(capsys.readouterr().out)
        assert out["items"][0]["volume_confirmed"] is False

    def test_default_volume_threshold_is_1_5(self, capsys):
        hist = _make_downtrend_then_recovery_with_volume_spike()
        with (
            patch("sys.argv", ["stock-screener", "signals", "7203"]),
            patch("stock_screener.cli.fetch_history", return_value=hist),
        ):
            main()
        out = json.loads(capsys.readouterr().out)
        # 最終日のみ出来高4倍 -> 既定閾値1.5で確認される
        assert out["items"][0]["volume_confirmed"] is True
