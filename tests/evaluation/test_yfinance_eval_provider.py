from __future__ import annotations

from unittest.mock import MagicMock, patch

from stock_screener.evaluation.domain.check import CheckStatus
from stock_screener.evaluation.infrastructure.yfinance_eval_provider import (
    YFinanceEvaluationDataProvider,
)
from stock_screener.shared.types import Ticker


class TestGetEarningsGrowthForecast:
    def test_returns_earnings_growth_from_yfinance(self):
        mock_ticker = MagicMock()
        mock_ticker.info = {"earningsGrowth": 0.25}

        with patch("yfinance.Ticker", return_value=mock_ticker):
            provider = YFinanceEvaluationDataProvider()
            result = provider.get_earnings_growth_forecast(Ticker("7203"))

        assert result == 0.25

    def test_returns_none_when_key_missing(self):
        mock_ticker = MagicMock()
        mock_ticker.info = {}

        with patch("yfinance.Ticker", return_value=mock_ticker):
            provider = YFinanceEvaluationDataProvider()
            result = provider.get_earnings_growth_forecast(Ticker("7203"))

        assert result is None

    def test_returns_none_when_value_is_none(self):
        mock_ticker = MagicMock()
        mock_ticker.info = {"earningsGrowth": None}

        with patch("yfinance.Ticker", return_value=mock_ticker):
            provider = YFinanceEvaluationDataProvider()
            result = provider.get_earnings_growth_forecast(Ticker("7203"))

        assert result is None

    def test_returns_none_on_exception(self):
        with patch("yfinance.Ticker", side_effect=Exception("network error")):
            provider = YFinanceEvaluationDataProvider()
            result = provider.get_earnings_growth_forecast(Ticker("7203"))

        assert result is None

    def test_negative_growth_returned(self):
        mock_ticker = MagicMock()
        mock_ticker.info = {"earningsGrowth": -0.15}

        with patch("yfinance.Ticker", return_value=mock_ticker):
            provider = YFinanceEvaluationDataProvider()
            result = provider.get_earnings_growth_forecast(Ticker("7203"))

        assert result == -0.15


class TestStubMethodsInherited:
    def test_check_accounting_fraud_returns_needs_review(self):
        provider = YFinanceEvaluationDataProvider()
        assert provider.check_accounting_fraud(Ticker("7203")) == CheckStatus.NEEDS_REVIEW

    def test_check_going_concern_returns_needs_review(self):
        provider = YFinanceEvaluationDataProvider()
        assert provider.check_going_concern(Ticker("7203")) == CheckStatus.NEEDS_REVIEW

    def test_get_margin_trading_ratio_returns_none(self):
        provider = YFinanceEvaluationDataProvider()
        assert provider.get_margin_trading_ratio(Ticker("7203")) is None

    def test_has_upward_revision_returns_none(self):
        provider = YFinanceEvaluationDataProvider()
        assert provider.has_upward_revision(Ticker("7203")) is None
