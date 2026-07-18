from __future__ import annotations

import dataclasses
from unittest.mock import MagicMock

import requests

from stock_screener.corporate_events.domain.earnings_date import EarningsDate
from stock_screener.corporate_events.infrastructure.jquants_earnings_provider import (
    JQuantsEarningsDateProvider,
)
from stock_screener.shared.types import Ticker


class TestEarningsDateHasNoTimeField:
    def test_no_time_related_fields_present(self):
        """DoD要件: EarningsDate は時刻を示すフィールドを一切持たない。"""
        field_names = {f.name for f in dataclasses.fields(EarningsDate)}
        time_related = {"time", "hour", "minute", "timestamp", "datetime", "announced_at"}
        assert field_names.isdisjoint(time_related)
        assert field_names == {"ticker", "date", "company_name", "fiscal_year", "fiscal_quarter"}


class TestGetEarningsDateNoClient:
    def test_returns_none_when_client_is_none(self):
        provider = JQuantsEarningsDateProvider(client=None)

        result = provider.get_earnings_date(Ticker("7203"))

        assert result is None


class TestGetEarningsDateFetchesData:
    def test_returns_none_when_no_results(self):
        mock_client = MagicMock()
        mock_client.get_earnings_calendar.return_value = []
        provider = JQuantsEarningsDateProvider(client=mock_client)

        result = provider.get_earnings_date(Ticker("7203"))

        assert result is None

    def test_maps_fields_correctly(self):
        mock_client = MagicMock()
        mock_client.get_earnings_calendar.return_value = [
            {
                "Date": "2025-01-31",
                "Code": "7203",
                "CoName": "テスト株式会社",
                "FY": "2025-03",
                "FQ": "3Q",
            },
        ]
        provider = JQuantsEarningsDateProvider(client=mock_client)

        result = provider.get_earnings_date(Ticker("7203"))

        assert result == EarningsDate(
            ticker="7203.T",
            date="2025-01-31",
            company_name="テスト株式会社",
            fiscal_year="2025-03",
            fiscal_quarter="3Q",
        )

    def test_passes_ticker_code_to_client(self):
        mock_client = MagicMock()
        mock_client.get_earnings_calendar.return_value = []
        provider = JQuantsEarningsDateProvider(client=mock_client)

        provider.get_earnings_date(Ticker("7203.T"))

        mock_client.get_earnings_calendar.assert_called_once_with(code="7203")


class TestGetEarningsDateRequestFailure:
    def test_returns_none_when_fetch_fails(self):
        mock_client = MagicMock()
        mock_client.get_earnings_calendar.side_effect = requests.exceptions.ConnectionError("boom")
        provider = JQuantsEarningsDateProvider(client=mock_client)

        result = provider.get_earnings_date(Ticker("7203"))

        assert result is None
