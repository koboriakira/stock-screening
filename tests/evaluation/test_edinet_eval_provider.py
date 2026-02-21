from __future__ import annotations

from unittest.mock import MagicMock, patch

import requests

from stock_screener.evaluation.domain.check import CheckStatus
from stock_screener.evaluation.infrastructure.edinet_eval_provider import (
    EdinetEvaluationDataProvider,
)
from stock_screener.shared.types import Ticker


def _make_filing(doc_type_code: str = "130", doc_description: str = "訂正有価証券報告書") -> dict:
    return {
        "docID": "S100ABC1",
        "secCode": "72030",
        "docTypeCode": doc_type_code,
        "filerName": "テスト株式会社",
        "docDescription": doc_description,
        "submitDateTime": "2025-01-15 09:00",
    }


class TestCheckAccountingFraud:
    def test_no_correction_reports_passes(self):
        mock_client = MagicMock()
        mock_client.find_filings_by_sec_code.return_value = []
        mock_client.ticker_to_sec_code.return_value = "72030"

        provider = EdinetEvaluationDataProvider(edinet_client=mock_client)
        result = provider.check_accounting_fraud(Ticker("7203"))

        assert result == CheckStatus.PASS

    def test_correction_report_returns_needs_review(self):
        mock_client = MagicMock()
        mock_client.find_filings_by_sec_code.return_value = [_make_filing()]
        mock_client.ticker_to_sec_code.return_value = "72030"

        provider = EdinetEvaluationDataProvider(edinet_client=mock_client)
        result = provider.check_accounting_fraud(Ticker("7203"))

        assert result == CheckStatus.NEEDS_REVIEW

    def test_searches_for_correction_reports(self):
        mock_client = MagicMock()
        mock_client.find_filings_by_sec_code.return_value = []
        mock_client.ticker_to_sec_code.return_value = "72030"

        provider = EdinetEvaluationDataProvider(edinet_client=mock_client)
        provider.check_accounting_fraud(Ticker("7203"))

        mock_client.find_filings_by_sec_code.assert_called_once_with(
            "72030", doc_type_codes=["130"], days=1095,
        )

    def test_returns_needs_review_on_error(self):
        mock_client = MagicMock()
        mock_client.find_filings_by_sec_code.side_effect = requests.exceptions.ConnectionError("API error")
        mock_client.ticker_to_sec_code.return_value = "72030"

        provider = EdinetEvaluationDataProvider(edinet_client=mock_client)
        result = provider.check_accounting_fraud(Ticker("7203"))

        assert result == CheckStatus.NEEDS_REVIEW


class TestCheckGoingConcern:
    def test_returns_needs_review_with_latest_report_info(self):
        mock_client = MagicMock()
        mock_client.find_filings_by_sec_code.return_value = [
            _make_filing(doc_type_code="120", doc_description="有価証券報告書"),
        ]
        mock_client.ticker_to_sec_code.return_value = "72030"

        provider = EdinetEvaluationDataProvider(edinet_client=mock_client)
        result = provider.check_going_concern(Ticker("7203"))

        assert result == CheckStatus.NEEDS_REVIEW

    def test_returns_needs_review_when_no_reports(self):
        mock_client = MagicMock()
        mock_client.find_filings_by_sec_code.return_value = []
        mock_client.ticker_to_sec_code.return_value = "72030"

        provider = EdinetEvaluationDataProvider(edinet_client=mock_client)
        result = provider.check_going_concern(Ticker("7203"))

        assert result == CheckStatus.NEEDS_REVIEW


class TestNoApiKey:
    def test_falls_back_to_stub_when_no_client(self):
        provider = EdinetEvaluationDataProvider(edinet_client=None)
        assert provider.check_accounting_fraud(Ticker("7203")) == CheckStatus.NEEDS_REVIEW
        assert provider.check_going_concern(Ticker("7203")) == CheckStatus.NEEDS_REVIEW


class TestInheritedMethods:
    def test_earnings_growth_inherited(self):
        mock_yf = MagicMock()
        mock_yf.info = {"earningsGrowth": 0.25}

        with patch("yfinance.Ticker", return_value=mock_yf):
            provider = EdinetEvaluationDataProvider(edinet_client=None)
            result = provider.get_earnings_growth_forecast(Ticker("7203"))

        assert result == 0.25
