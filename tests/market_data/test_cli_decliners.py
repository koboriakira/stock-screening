from __future__ import annotations

import json
from unittest.mock import patch

import pandas as pd
import pytest

from stock_screener.cli import TEST_MODE_LIMIT, main


def _hist(prev_close: float, close: float, volume: int = 1000) -> pd.DataFrame:
    return pd.DataFrame(
        [{"Close": prev_close, "Volume": volume}, {"Close": close, "Volume": volume}],
        index=pd.DatetimeIndex(["2026-07-16", "2026-07-17"]),
    )


def _jpx_row(code: str, name: str) -> dict:
    return {"ticker": code, "company_name": name, "sector": "test", "market": "プライム"}


class TestCliDeclinersSuccess:
    def test_returns_ranked_json(self, capsys):
        universe = [_jpx_row("1000", "会社A"), _jpx_row("1001", "会社B")]
        hist_map = {
            "1000.T": _hist(prev_close=100, close=99),  # -1%
            "1001.T": _hist(prev_close=100, close=90),  # -10%
        }
        with (
            patch("sys.argv", ["stock-screener", "decliners", "--top", "5"]),
            patch("stock_screener.cli.JpxStockListFetcher") as mock_jpx_cls,
            patch("stock_screener.cli.fetch_history", side_effect=lambda symbol, **_kw: hist_map[symbol]),
        ):
            mock_jpx_cls.return_value.fetch.return_value = universe
            main()

        out = json.loads(capsys.readouterr().out)
        assert out["type"] == "decliners"
        assert out["source"] == "yfinance+jpx"
        assert out["count"] == 2
        assert out["items"][0]["ticker"] == "1001.T"
        assert out["items"][0]["change_pct"] == -10.0
        assert out["items"][1]["ticker"] == "1000.T"


class TestCliDeclinersTopTruncation:
    def test_top_option_truncates(self, capsys):
        universe = [_jpx_row(str(1000 + i), f"会社{i}") for i in range(5)]
        with (
            patch("sys.argv", ["stock-screener", "decliners", "--top", "2"]),
            patch("stock_screener.cli.JpxStockListFetcher") as mock_jpx_cls,
            patch(
                "stock_screener.cli.fetch_history",
                side_effect=lambda _symbol, **_kw: _hist(prev_close=100, close=99),
            ),
        ):
            mock_jpx_cls.return_value.fetch.return_value = universe
            main()

        out = json.loads(capsys.readouterr().out)
        assert out["count"] == 2


class TestCliDeclinersTestMode:
    def test_test_flag_limits_universe(self, capsys):
        universe = [_jpx_row(str(1000 + i), f"会社{i}") for i in range(50)]
        with (
            patch("sys.argv", ["stock-screener", "decliners", "--test", "--top", "100"]),
            patch("stock_screener.cli.JpxStockListFetcher") as mock_jpx_cls,
            patch(
                "stock_screener.cli.fetch_history",
                side_effect=lambda _symbol, **_kw: _hist(prev_close=100, close=99),
            ) as mock_fetch,
        ):
            mock_jpx_cls.return_value.fetch.return_value = universe
            main()

        out = json.loads(capsys.readouterr().out)
        assert out["count"] == TEST_MODE_LIMIT
        assert mock_fetch.call_count == TEST_MODE_LIMIT


class TestCliDeclinersPartialFailure:
    def test_fetch_failure_goes_to_errors(self, capsys):
        universe = [_jpx_row("1000", "会社A"), _jpx_row("1001", "会社B")]

        def fetch(symbol: str, **_kw):
            if symbol == "1000.T":
                return pd.DataFrame()
            return _hist(prev_close=100, close=99)

        with (
            patch("sys.argv", ["stock-screener", "decliners"]),
            patch("stock_screener.cli.JpxStockListFetcher") as mock_jpx_cls,
            patch("stock_screener.cli.fetch_history", side_effect=fetch),
        ):
            mock_jpx_cls.return_value.fetch.return_value = universe
            main()

        out = json.loads(capsys.readouterr().out)
        assert out["count"] == 1
        assert len(out["errors"]) == 1
        assert out["errors"][0]["ticker"] == "1000.T"
        assert out["errors"][0]["code"] == "no_data"


class TestCliDeclinersUniverseFetchFailed:
    def test_universe_fetch_error_exits_1(self, capsys):
        with (
            patch("sys.argv", ["stock-screener", "decliners"]),
            patch("stock_screener.cli.JpxStockListFetcher") as mock_jpx_cls,
        ):
            mock_jpx_cls.return_value.fetch.side_effect = Exception("boom")
            with pytest.raises(SystemExit) as exc_info:
                main()
        assert exc_info.value.code == 1
        out = json.loads(capsys.readouterr().out)
        assert out["type"] == "error"


class TestCliDeclinersDefaultTop:
    def test_default_top_is_20(self, capsys):
        universe = [_jpx_row(str(1000 + i), f"会社{i}") for i in range(3)]
        with (
            patch("sys.argv", ["stock-screener", "decliners"]),
            patch("stock_screener.cli.JpxStockListFetcher") as mock_jpx_cls,
            patch(
                "stock_screener.cli.fetch_history",
                side_effect=lambda _symbol, **_kw: _hist(prev_close=100, close=99),
            ),
        ):
            mock_jpx_cls.return_value.fetch.return_value = universe
            main()

        out = json.loads(capsys.readouterr().out)
        assert out["count"] == 3
