from __future__ import annotations

from unittest.mock import MagicMock, patch

import requests

from stock_screener.corporate_events.infrastructure.large_holding_provider import (
    EdinetLargeHoldingProvider,
)
from stock_screener.shared.types import Ticker


class TestGetLargeHoldingsNoClient:
    def test_returns_none_when_edinet_client_is_none(self):
        provider = EdinetLargeHoldingProvider(edinet_client=None)

        result = provider.get_large_holdings(Ticker("7203"))

        assert result is None


class TestGetLargeHoldingsIssuerCodeNotFound:
    def test_returns_empty_list_when_issuer_edinet_code_not_found(self):
        mock_client = MagicMock()
        mock_code_list_fetcher = MagicMock()
        mock_code_list_fetcher.find_issuer_edinet_code.return_value = None
        provider = EdinetLargeHoldingProvider(
            edinet_client=mock_client,
            code_list_fetcher=mock_code_list_fetcher,
        )

        result = provider.get_large_holdings(Ticker("7203"))

        assert result == []
        mock_client.find_filings_by_issuer_edinet_code.assert_not_called()


class TestGetLargeHoldingsFetchesFilings:
    def test_uses_doc_type_codes_350_and_360(self):
        mock_client = MagicMock()
        mock_client.find_filings_by_issuer_edinet_code.return_value = []
        mock_code_list_fetcher = MagicMock()
        mock_code_list_fetcher.find_issuer_edinet_code.return_value = "E00004"
        provider = EdinetLargeHoldingProvider(
            edinet_client=mock_client,
            code_list_fetcher=mock_code_list_fetcher,
        )

        provider.get_large_holdings(Ticker("7203"), days=90)

        mock_client.find_filings_by_issuer_edinet_code.assert_called_once_with(
            "E00004",
            doc_type_codes=["350", "360"],
            days=90,
        )

    def test_converts_docs_to_large_holding_filings(self):
        mock_client = MagicMock()
        mock_client.find_filings_by_issuer_edinet_code.return_value = [
            {
                "docID": "S100ABC1",
                "submitDateTime": "2025-01-15 09:00",
                "filerName": "テストファンド株式会社",
                "secCode": "99990",
                "docTypeCode": "350",
            },
        ]
        mock_code_list_fetcher = MagicMock()
        mock_code_list_fetcher.find_issuer_edinet_code.return_value = "E00004"
        provider = EdinetLargeHoldingProvider(
            edinet_client=mock_client,
            code_list_fetcher=mock_code_list_fetcher,
        )

        result = provider.get_large_holdings(Ticker("7203"))

        assert result is not None
        assert len(result) == 1
        assert result[0].doc_id == "S100ABC1"
        assert result[0].filer_name == "テストファンド株式会社"

    def test_passes_sec_code_derived_from_ticker(self):
        mock_client = MagicMock()
        mock_client.find_filings_by_issuer_edinet_code.return_value = []
        mock_code_list_fetcher = MagicMock()
        mock_code_list_fetcher.find_issuer_edinet_code.return_value = "E00004"
        provider = EdinetLargeHoldingProvider(
            edinet_client=mock_client,
            code_list_fetcher=mock_code_list_fetcher,
        )

        provider.get_large_holdings(Ticker("7203"))

        mock_code_list_fetcher.find_issuer_edinet_code.assert_called_once_with("72030")


class TestGetLargeHoldingsRequestFailure:
    def test_returns_none_when_code_list_fetch_fails(self):
        mock_client = MagicMock()
        mock_code_list_fetcher = MagicMock()
        mock_code_list_fetcher.find_issuer_edinet_code.side_effect = requests.exceptions.ConnectionError(
            "boom",
        )
        provider = EdinetLargeHoldingProvider(
            edinet_client=mock_client,
            code_list_fetcher=mock_code_list_fetcher,
        )

        result = provider.get_large_holdings(Ticker("7203"))

        assert result is None

    def test_returns_none_when_filings_fetch_fails(self):
        mock_client = MagicMock()
        mock_client.find_filings_by_issuer_edinet_code.side_effect = requests.exceptions.ConnectionError(
            "boom",
        )
        mock_code_list_fetcher = MagicMock()
        mock_code_list_fetcher.find_issuer_edinet_code.return_value = "E00004"
        provider = EdinetLargeHoldingProvider(
            edinet_client=mock_client,
            code_list_fetcher=mock_code_list_fetcher,
        )

        result = provider.get_large_holdings(Ticker("7203"))

        assert result is None


class TestEdinetLargeHoldingProviderDefaultCodeListFetcher:
    def test_builds_default_code_list_fetcher_with_168h_ttl_cache(self):
        with (
            patch(
                "stock_screener.corporate_events.infrastructure.large_holding_provider.EdinetCodeListFetcher",
            ) as mock_fetcher_cls,
            patch(
                "stock_screener.corporate_events.infrastructure.large_holding_provider.FileCache",
            ) as mock_cache_cls,
        ):
            EdinetLargeHoldingProvider(edinet_client=None)

        mock_cache_cls.assert_called_once_with(ttl_hours=168)
        mock_fetcher_cls.assert_called_once_with(cache=mock_cache_cls.return_value)
