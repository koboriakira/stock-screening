from __future__ import annotations

from unittest.mock import MagicMock, patch

import requests

from stock_screener.evaluation.infrastructure.edinet_client import EdinetClient


def _make_documents_response(results: list[dict]) -> dict:
    return {
        "metadata": {
            "title": "提出された書類を把握するためのAPI",
            "parameter": {"date": "2025-01-15", "type": "2"},
            "resultset": {"count": len(results)},
            "status": "200",
            "message": "OK",
        },
        "results": results,
    }


def _make_filing(
    doc_id: str = "S100ABC1",
    sec_code: str = "72030",
    doc_type_code: str = "120",
    filer_name: str = "テスト株式会社",
    doc_description: str = "有価証券報告書",
    submit_date_time: str = "2025-01-15 09:00",
) -> dict:
    return {
        "docID": doc_id,
        "secCode": sec_code,
        "docTypeCode": doc_type_code,
        "filerName": filer_name,
        "docDescription": doc_description,
        "submitDateTime": submit_date_time,
        "edinetCode": "E00001",
    }


class TestGetDocuments:
    def test_returns_results_from_api(self):
        filing = _make_filing()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = _make_documents_response([filing])

        with patch("requests.get", return_value=mock_response) as mock_get:
            client = EdinetClient(api_key="test-key")
            results = client.get_documents("2025-01-15")

        assert len(results) == 1
        assert results[0]["docID"] == "S100ABC1"
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert call_args[1]["params"]["Subscription-Key"] == "test-key"
        assert call_args[1]["params"]["date"] == "2025-01-15"

    def test_returns_empty_on_api_error(self):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("Server Error")

        with patch("requests.get", return_value=mock_response):
            client = EdinetClient(api_key="test-key")
            results = client.get_documents("2025-01-15")

        assert results == []

    def test_returns_empty_on_network_error(self):
        with patch("requests.get", side_effect=requests.exceptions.ConnectionError("Connection refused")):
            client = EdinetClient(api_key="test-key")
            results = client.get_documents("2025-01-15")

        assert results == []


class TestFindFilingsBySecCode:
    def test_finds_matching_filings(self):
        target = _make_filing(sec_code="72030", doc_type_code="120")
        other = _make_filing(sec_code="99990", doc_type_code="120")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = _make_documents_response([target, other])

        with patch("requests.get", return_value=mock_response):
            client = EdinetClient(api_key="test-key")
            results = client.find_filings_by_sec_code("72030", doc_type_codes=["120"], days=1)

        assert len(results) == 1
        assert results[0]["secCode"] == "72030"

    def test_filters_by_doc_type(self):
        report_120 = _make_filing(sec_code="72030", doc_type_code="120")
        report_130 = _make_filing(sec_code="72030", doc_type_code="130")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = _make_documents_response([report_120, report_130])

        with patch("requests.get", return_value=mock_response):
            client = EdinetClient(api_key="test-key")
            results = client.find_filings_by_sec_code("72030", doc_type_codes=["130"], days=1)

        assert len(results) == 1
        assert results[0]["docTypeCode"] == "130"

    def test_searches_multiple_days(self):
        call_count = 0
        filing = _make_filing(sec_code="72030", doc_type_code="120")

        def mock_get(*_args, **_kwargs):
            nonlocal call_count
            call_count += 1
            resp = MagicMock()
            resp.status_code = 200
            if call_count == 1:
                resp.json.return_value = _make_documents_response([filing])
            else:
                resp.json.return_value = _make_documents_response([])
            return resp

        with patch("requests.get", side_effect=mock_get):
            client = EdinetClient(api_key="test-key")
            results = client.find_filings_by_sec_code("72030", doc_type_codes=["120"], days=3)

        assert len(results) == 1
        assert call_count == 3

    def test_returns_empty_when_no_match(self):
        filing = _make_filing(sec_code="99990", doc_type_code="120")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = _make_documents_response([filing])

        with patch("requests.get", return_value=mock_response):
            client = EdinetClient(api_key="test-key")
            results = client.find_filings_by_sec_code("72030", doc_type_codes=["120"], days=1)

        assert results == []

    def test_handles_none_sec_code_in_results(self):
        filing = _make_filing(sec_code=None, doc_type_code="120")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = _make_documents_response([filing])

        with patch("requests.get", return_value=mock_response):
            client = EdinetClient(api_key="test-key")
            results = client.find_filings_by_sec_code("72030", doc_type_codes=["120"], days=1)

        assert results == []


class TestTickerToSecCode:
    def test_4digit_ticker(self):
        assert EdinetClient.ticker_to_sec_code("7203") == "72030"

    def test_5digit_ticker(self):
        assert EdinetClient.ticker_to_sec_code("25935") == "25935"

    def test_with_suffix(self):
        assert EdinetClient.ticker_to_sec_code("7203.T") == "72030"
