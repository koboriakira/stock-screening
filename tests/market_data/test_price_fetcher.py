from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
import requests

from stock_screener.market_data.infrastructure.price_fetcher import fetch_history


class TestFetchHistory:
    def test_calls_yfinance_with_symbol_period_interval(self):
        mock_df = pd.DataFrame({"Close": [100.0]})
        mock_yf_ticker = MagicMock()
        mock_yf_ticker.history.return_value = mock_df

        with patch("yfinance.Ticker", return_value=mock_yf_ticker) as mock_cls:
            result = fetch_history("7203.T", period="3mo", interval="1d")

        mock_cls.assert_called_once_with("7203.T")
        mock_yf_ticker.history.assert_called_once_with(period="3mo", interval="1d")
        assert result is mock_df

    def test_default_interval_is_1d(self):
        mock_df = pd.DataFrame({"Close": [100.0]})
        mock_yf_ticker = MagicMock()
        mock_yf_ticker.history.return_value = mock_df

        with patch("yfinance.Ticker", return_value=mock_yf_ticker):
            fetch_history("7203.T", period="5d")

        mock_yf_ticker.history.assert_called_once_with(period="5d", interval="1d")

    def test_propagates_exception_after_retries_exhausted(self):
        mock_yf_ticker = MagicMock()
        mock_yf_ticker.history.side_effect = requests.exceptions.ConnectionError("timeout")

        with (
            patch("yfinance.Ticker", return_value=mock_yf_ticker),
            patch("stock_screener.shared.retry.time.sleep"),
            pytest.raises(requests.exceptions.ConnectionError),
        ):
            fetch_history("7203.T", period="5d")

    def test_no_cache_calls_yfinance_every_time(self):
        mock_df = pd.DataFrame({"Close": [100.0]})
        mock_yf_ticker = MagicMock()
        mock_yf_ticker.history.return_value = mock_df

        with patch("yfinance.Ticker", return_value=mock_yf_ticker) as mock_cls:
            fetch_history("7203.T", period="5d")
            fetch_history("7203.T", period="5d")

        assert mock_cls.call_count == 2
