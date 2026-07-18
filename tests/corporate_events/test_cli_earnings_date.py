from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from stock_screener.cli import _build_earnings_date_provider, main
from stock_screener.corporate_events.domain.earnings_date import EarningsDate
from stock_screener.corporate_events.infrastructure.jquants_earnings_provider import (
    JQuantsEarningsDateProvider,
)


def _patch_provider(provider):
    return patch("stock_screener.cli._build_earnings_date_provider", return_value=provider)


class TestCliEarningsDateNeedsReview:
    def test_client_none_returns_needs_review(self, capsys):
        """J_QUANTS_API_KEY 未設定時は status: needs_review を返す。"""
        provider = JQuantsEarningsDateProvider(client=None)
        with (
            patch("sys.argv", ["stock-screener", "earnings-date", "7203.T"]),
            _patch_provider(provider),
        ):
            main()

        out = json.loads(capsys.readouterr().out)
        assert out["type"] == "earnings-date"
        assert out["count"] == 1
        item = out["items"][0]
        assert item["ticker"] == "7203.T"
        assert item["status"] == "needs_review"
        assert item["date"] is None
        assert item["company_name"] is None
        assert item["fiscal_year"] is None
        assert item["fiscal_quarter"] is None

    def test_no_data_available_also_returns_needs_review(self, capsys):
        mock_provider = MagicMock()
        mock_provider.get_earnings_date.return_value = None
        with (
            patch("sys.argv", ["stock-screener", "earnings-date", "7203.T"]),
            _patch_provider(mock_provider),
        ):
            main()

        out = json.loads(capsys.readouterr().out)
        item = out["items"][0]
        assert item["status"] == "needs_review"


class TestCliEarningsDateOk:
    def test_returns_earnings_date_when_available(self, capsys):
        earnings_date = EarningsDate(
            ticker="7203.T",
            date="2025-01-31",
            company_name="テスト株式会社",
            fiscal_year="2025-03",
            fiscal_quarter="3Q",
        )
        mock_provider = MagicMock()
        mock_provider.get_earnings_date.return_value = earnings_date
        with (
            patch("sys.argv", ["stock-screener", "earnings-date", "7203.T"]),
            _patch_provider(mock_provider),
        ):
            main()

        out = json.loads(capsys.readouterr().out)
        item = out["items"][0]
        assert item["status"] == "ok"
        assert item["date"] == "2025-01-31"
        assert item["company_name"] == "テスト株式会社"
        assert item["fiscal_year"] == "2025-03"
        assert item["fiscal_quarter"] == "3Q"

    def test_no_time_related_keys_in_json_output(self, capsys):
        """DoD要件: JSON出力にも時刻フィールドが含まれないことを確認する。"""
        earnings_date = EarningsDate(
            ticker="7203.T",
            date="2025-01-31",
            company_name="テスト株式会社",
            fiscal_year="2025-03",
            fiscal_quarter="3Q",
        )
        mock_provider = MagicMock()
        mock_provider.get_earnings_date.return_value = earnings_date
        with (
            patch("sys.argv", ["stock-screener", "earnings-date", "7203.T"]),
            _patch_provider(mock_provider),
        ):
            main()

        out = json.loads(capsys.readouterr().out)
        item = out["items"][0]
        time_related = {"time", "hour", "minute", "timestamp", "datetime", "announced_at"}
        assert time_related.isdisjoint(item.keys())


class TestCliEarningsDateMultipleTickers:
    def test_multiple_tickers_produce_multiple_items(self, capsys):
        mock_provider = MagicMock()
        mock_provider.get_earnings_date.return_value = None
        with (
            patch("sys.argv", ["stock-screener", "earnings-date", "7203.T", "6758.T"]),
            _patch_provider(mock_provider),
        ):
            main()

        out = json.loads(capsys.readouterr().out)
        assert out["count"] == 2
        assert [item["ticker"] for item in out["items"]] == ["7203.T", "6758.T"]


class TestCliEarningsDateJsonEnvelope:
    def test_envelope_has_expected_keys(self, capsys):
        mock_provider = MagicMock()
        mock_provider.get_earnings_date.return_value = None
        with (
            patch("sys.argv", ["stock-screener", "earnings-date", "7203.T"]),
            _patch_provider(mock_provider),
        ):
            main()

        out = json.loads(capsys.readouterr().out)
        assert set(out.keys()) == {"type", "count", "items", "source", "fetched_at", "cache_hit"}
        assert out["source"] == "jquants"
        assert out["cache_hit"] is False


class TestBuildEarningsDateProvider:
    def test_env_var_unset_does_not_construct_client(self):
        with (
            patch.dict("os.environ", {}, clear=True),
            patch("stock_screener.cli.JQuantsClient") as mock_client_cls,
        ):
            _build_earnings_date_provider()

        mock_client_cls.assert_not_called()

    def test_env_var_set_constructs_client_with_key(self):
        with (
            patch.dict("os.environ", {"J_QUANTS_API_KEY": "test-key"}, clear=False),
            patch("stock_screener.cli.JQuantsClient") as mock_client_cls,
        ):
            _build_earnings_date_provider()

        mock_client_cls.assert_called_once_with(api_key="test-key")
