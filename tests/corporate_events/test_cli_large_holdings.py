from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from stock_screener.cli import main
from stock_screener.corporate_events.domain.large_holding import LargeHoldingFiling
from stock_screener.corporate_events.infrastructure.large_holding_provider import (
    EdinetLargeHoldingProvider,
)


def _patch_provider(provider):
    return patch("stock_screener.cli._build_large_holdings_provider", return_value=provider)


class TestCliLargeHoldingsNeedsReview:
    def test_edinet_client_none_returns_needs_review(self, capsys):
        provider = EdinetLargeHoldingProvider(edinet_client=None)
        with (
            patch("sys.argv", ["stock-screener", "large-holdings", "7203.T"]),
            _patch_provider(provider),
        ):
            main()

        out = json.loads(capsys.readouterr().out)
        assert out["type"] == "large-holdings"
        assert out["count"] == 1
        item = out["items"][0]
        assert item["ticker"] == "7203.T"
        assert item["status"] == "needs_review"
        assert item["filings"] == []


class TestCliLargeHoldingsOk:
    def test_returns_filings_when_available(self, capsys):
        filing = LargeHoldingFiling(
            doc_id="S100ABC1",
            submitted_at="2025-01-15 09:00",
            filer_name="テストファンド株式会社",
            filer_sec_code="99990",
            doc_type_code="350",
        )
        mock_provider = MagicMock()
        mock_provider.get_large_holdings.return_value = [filing]
        with (
            patch("sys.argv", ["stock-screener", "large-holdings", "7203.T"]),
            _patch_provider(mock_provider),
        ):
            main()

        out = json.loads(capsys.readouterr().out)
        item = out["items"][0]
        assert item["status"] == "ok"
        assert item["filings"] == [
            {
                "doc_id": "S100ABC1",
                "submitted_at": "2025-01-15 09:00",
                "filer_name": "テストファンド株式会社",
                "filer_sec_code": "99990",
                "doc_type_code": "350",
            },
        ]

    def test_empty_filings_list_is_ok_not_needs_review(self, capsys):
        mock_provider = MagicMock()
        mock_provider.get_large_holdings.return_value = []
        with (
            patch("sys.argv", ["stock-screener", "large-holdings", "7203.T"]),
            _patch_provider(mock_provider),
        ):
            main()

        out = json.loads(capsys.readouterr().out)
        item = out["items"][0]
        assert item["status"] == "ok"
        assert item["filings"] == []


class TestCliLargeHoldingsMultipleTickers:
    def test_multiple_tickers_produce_multiple_items(self, capsys):
        mock_provider = MagicMock()
        mock_provider.get_large_holdings.return_value = []
        with (
            patch("sys.argv", ["stock-screener", "large-holdings", "7203.T", "6758.T"]),
            _patch_provider(mock_provider),
        ):
            main()

        out = json.loads(capsys.readouterr().out)
        assert out["count"] == 2
        assert [item["ticker"] for item in out["items"]] == ["7203.T", "6758.T"]


class TestCliLargeHoldingsDaysOption:
    def test_default_days_is_90(self, capsys):
        mock_provider = MagicMock()
        mock_provider.get_large_holdings.return_value = []
        with (
            patch("sys.argv", ["stock-screener", "large-holdings", "7203.T"]),
            _patch_provider(mock_provider),
        ):
            main()

        mock_provider.get_large_holdings.assert_called_once()
        _, kwargs = mock_provider.get_large_holdings.call_args
        assert kwargs["days"] == 90

    def test_custom_days_is_passed_through(self, capsys):
        mock_provider = MagicMock()
        mock_provider.get_large_holdings.return_value = []
        with (
            patch("sys.argv", ["stock-screener", "large-holdings", "7203.T", "--days", "30"]),
            _patch_provider(mock_provider),
        ):
            main()

        _, kwargs = mock_provider.get_large_holdings.call_args
        assert kwargs["days"] == 30


class TestCliLargeHoldingsJsonEnvelope:
    def test_envelope_has_expected_keys(self, capsys):
        mock_provider = MagicMock()
        mock_provider.get_large_holdings.return_value = []
        with (
            patch("sys.argv", ["stock-screener", "large-holdings", "7203.T"]),
            _patch_provider(mock_provider),
        ):
            main()

        out = json.loads(capsys.readouterr().out)
        assert set(out.keys()) == {"type", "count", "items", "source", "fetched_at", "cache_hit"}
        assert out["source"] == "edinet"
        assert out["cache_hit"] is False
