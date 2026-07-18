from __future__ import annotations

from unittest.mock import MagicMock

from stock_screener.corporate_events.service import EarningsDateService, LargeHoldingsService
from stock_screener.shared.types import Ticker


class TestLargeHoldingsServiceFetch:
    def test_delegates_to_provider_with_days(self):
        mock_provider = MagicMock()
        mock_provider.get_large_holdings.return_value = []
        service = LargeHoldingsService(mock_provider)

        result = service.fetch(Ticker("7203"), days=30)

        mock_provider.get_large_holdings.assert_called_once_with(Ticker("7203"), days=30)
        assert result == []

    def test_default_days_is_90(self):
        mock_provider = MagicMock()
        mock_provider.get_large_holdings.return_value = []
        service = LargeHoldingsService(mock_provider)

        service.fetch(Ticker("7203"))

        mock_provider.get_large_holdings.assert_called_once_with(Ticker("7203"), days=90)

    def test_passes_through_none(self):
        mock_provider = MagicMock()
        mock_provider.get_large_holdings.return_value = None
        service = LargeHoldingsService(mock_provider)

        result = service.fetch(Ticker("7203"))

        assert result is None


class TestEarningsDateServiceFetch:
    def test_delegates_to_provider(self):
        mock_provider = MagicMock()
        mock_provider.get_earnings_date.return_value = None
        service = EarningsDateService(mock_provider)

        result = service.fetch(Ticker("7203"))

        mock_provider.get_earnings_date.assert_called_once_with(Ticker("7203"))
        assert result is None
