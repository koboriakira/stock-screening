from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from stock_screener.cli import main


def _make_mock_jpx_data() -> list[dict]:
    return [
        {"ticker": "7203", "company_name": "トヨタ自動車", "sector": "輸送用機器", "market": "プライム"},
        {"ticker": "1002", "company_name": "テスト株B", "sector": "機械", "market": "スタンダード"},
    ]


class TestCliUniverseAll:
    def test_returns_all_items(self, capsys):
        with (
            patch("sys.argv", ["stock-screener", "universe"]),
            patch("stock_screener.cli.JpxStockListFetcher") as mock_jpx_cls,
        ):
            mock_jpx_cls.return_value.fetch.return_value = _make_mock_jpx_data()
            main()
        out = json.loads(capsys.readouterr().out)
        assert out["type"] == "universe"
        assert out["count"] == 2
        item = out["items"][0]
        assert item["code"] == "7203"
        assert item["ticker"] == "7203.T"
        assert item["company_name"] == "トヨタ自動車"
        assert item["sector"] == "輸送用機器"
        assert item["market"] == "プライム"
        assert out["source"] == "jpx"


class TestCliUniverseMarketFilter:
    def test_partial_match_filters(self, capsys):
        with (
            patch("sys.argv", ["stock-screener", "universe", "--market", "プライム"]),
            patch("stock_screener.cli.JpxStockListFetcher") as mock_jpx_cls,
        ):
            mock_jpx_cls.return_value.fetch.return_value = _make_mock_jpx_data()
            main()
        out = json.loads(capsys.readouterr().out)
        assert out["count"] == 1
        assert out["items"][0]["ticker"] == "7203.T"


class TestCliUniverseNoMatch:
    def test_zero_matches_is_success(self, capsys):
        with (
            patch("sys.argv", ["stock-screener", "universe", "--market", "存在しない区分"]),
            patch("stock_screener.cli.JpxStockListFetcher") as mock_jpx_cls,
        ):
            mock_jpx_cls.return_value.fetch.return_value = _make_mock_jpx_data()
            main()
        out = json.loads(capsys.readouterr().out)
        assert out["count"] == 0
        assert out["items"] == []


class TestCliUniverseFetchFailed:
    def test_fetch_error_exits_1(self, capsys):
        with (
            patch("sys.argv", ["stock-screener", "universe"]),
            patch("stock_screener.cli.JpxStockListFetcher") as mock_jpx_cls,
        ):
            mock_jpx_cls.return_value.fetch.side_effect = Exception("boom")
            with pytest.raises(SystemExit) as exc_info:
                main()
        assert exc_info.value.code == 1
        out = json.loads(capsys.readouterr().out)
        assert out["type"] == "error"
