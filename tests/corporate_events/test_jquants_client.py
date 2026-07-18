from __future__ import annotations

from unittest.mock import MagicMock, patch

import requests

from stock_screener.corporate_events.infrastructure.jquants_client import JQuantsClient


def _make_earnings_calendar_response(results: list[dict]) -> dict:
    return {
        "earnings_calendar": results,
        "pagination_key": None,
    }


def _make_entry(
    date: str = "2025-01-31",
    code: str = "7203",
    co_name: str = "テスト株式会社",
    fy: str = "2025-03",
    fq: str = "3Q",
) -> dict:
    return {
        "Date": date,
        "Code": code,
        "CoName": co_name,
        "FY": fy,
        "FQ": fq,
        "SectorNm": "輸送用機器",
        "Section": "プライム",
    }


class TestGetEarningsCalendar:
    def test_returns_results_from_api(self):
        entry = _make_entry()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = _make_earnings_calendar_response([entry])

        with patch("requests.get", return_value=mock_response) as mock_get:
            client = JQuantsClient(api_key="test-key")
            results = client.get_earnings_calendar()

        assert len(results) == 1
        assert results[0]["Code"] == "7203"
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert call_args[1]["headers"]["Authorization"] == "Bearer test-key"

    def test_filters_by_code_when_specified(self):
        target = _make_entry(code="7203")
        other = _make_entry(code="6758")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = _make_earnings_calendar_response([target, other])

        with patch("requests.get", return_value=mock_response) as mock_get:
            client = JQuantsClient(api_key="test-key")
            results = client.get_earnings_calendar(code="7203")

        assert len(results) == 1
        assert results[0]["Code"] == "7203"
        call_args = mock_get.call_args
        assert call_args[1]["params"]["code"] == "7203"

    def test_returns_empty_on_api_error(self):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("Server Error")

        with patch("requests.get", return_value=mock_response):
            client = JQuantsClient(api_key="test-key")
            results = client.get_earnings_calendar()

        assert results == []

    def test_returns_empty_on_network_error(self):
        with patch("requests.get", side_effect=requests.exceptions.ConnectionError("Connection refused")):
            client = JQuantsClient(api_key="test-key")
            results = client.get_earnings_calendar()

        assert results == []

    def test_returns_empty_when_no_match_for_code(self):
        other = _make_entry(code="6758")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = _make_earnings_calendar_response([other])

        with patch("requests.get", return_value=mock_response):
            client = JQuantsClient(api_key="test-key")
            results = client.get_earnings_calendar(code="7203")

        assert results == []
