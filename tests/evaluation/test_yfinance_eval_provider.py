from __future__ import annotations

from unittest.mock import MagicMock, PropertyMock, patch

import pandas as pd
import requests

from stock_screener.evaluation.domain.check import CheckStatus
from stock_screener.evaluation.infrastructure.yfinance_eval_provider import (
    YFinanceEvaluationDataProvider,
    compute_per_percentile,
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
        with patch("yfinance.Ticker", side_effect=requests.exceptions.ConnectionError("network error")):
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


def _make_monthly_prices(prices: list[float], start: str = "2021-01-01") -> pd.DataFrame:
    dates = pd.date_range(start, periods=len(prices), freq="MS")
    return pd.DataFrame({"Close": prices}, index=dates)


def _make_eps_series(eps_dict: dict) -> pd.Series:
    index = [pd.Timestamp(k) for k in eps_dict]
    return pd.Series(list(eps_dict.values()), index=index, name="Diluted EPS")


class TestComputePerPercentile:
    def test_current_per_at_minimum_returns_low_percentile(self):
        # PERレンジ: 5~20、現在PER=5 → パーセンタイル≒0
        prices = [100.0] * 12 + [200.0] * 12 + [300.0] * 12 + [400.0] * 12
        monthly = _make_monthly_prices(prices, "2021-01-01")
        eps = _make_eps_series({
            "2024-03-31": 20.0,
            "2023-03-31": 20.0,
            "2022-03-31": 20.0,
            "2021-03-31": 20.0,
        })
        # 現在PER = 100/20 = 5, 最大PER = 400/20 = 20
        result = compute_per_percentile(monthly, eps, current_per=5.0)
        assert result is not None
        assert result <= 25.0

    def test_current_per_at_maximum_returns_high_percentile(self):
        prices = [100.0] * 12 + [200.0] * 12 + [300.0] * 12 + [400.0] * 12
        monthly = _make_monthly_prices(prices, "2021-01-01")
        eps = _make_eps_series({
            "2024-03-31": 20.0,
            "2023-03-31": 20.0,
            "2022-03-31": 20.0,
            "2021-03-31": 20.0,
        })
        # 現在PER = 400/20 = 20 (最大値)
        result = compute_per_percentile(monthly, eps, current_per=20.0)
        assert result is not None
        assert result >= 75.0

    def test_returns_none_for_empty_prices(self):
        monthly = _make_monthly_prices([])
        eps = _make_eps_series({"2024-03-31": 20.0})
        result = compute_per_percentile(monthly, eps, current_per=10.0)
        assert result is None

    def test_returns_none_for_empty_eps(self):
        monthly = _make_monthly_prices([100.0] * 12)
        eps = _make_eps_series({})
        result = compute_per_percentile(monthly, eps, current_per=10.0)
        assert result is None

    def test_negative_eps_excluded(self):
        prices = [100.0] * 24
        monthly = _make_monthly_prices(prices, "2022-01-01")
        eps = _make_eps_series({
            "2023-03-31": -10.0,
            "2022-03-31": 20.0,
        })
        result = compute_per_percentile(monthly, eps, current_per=5.0)
        assert result is not None


class TestGetPerPercentileInRange:
    def test_returns_percentile_from_yfinance(self):
        mock_ticker = MagicMock()
        mock_ticker.info = {"trailingPE": 10.0}

        prices = [100.0] * 48
        history_df = _make_monthly_prices(prices, "2021-01-01")
        mock_ticker.history.return_value = history_df

        eps_data = _make_eps_series({
            "2024-03-31": 10.0,
            "2023-03-31": 10.0,
            "2022-03-31": 10.0,
            "2021-03-31": 10.0,
        })
        financials_df = pd.DataFrame({"col": [0]}, index=["Other"])
        financials_df = pd.concat([
            financials_df,
            pd.DataFrame([eps_data.to_dict()], index=["Diluted EPS"]),
        ])
        type(mock_ticker).financials = PropertyMock(return_value=financials_df)

        with patch("yfinance.Ticker", return_value=mock_ticker):
            provider = YFinanceEvaluationDataProvider()
            result = provider.get_per_percentile_in_5y_range(Ticker("7203"))

        assert result is not None
        assert 0.0 <= result <= 100.0

    def test_returns_none_on_exception(self):
        with patch("yfinance.Ticker", side_effect=requests.exceptions.ConnectionError("network error")):
            provider = YFinanceEvaluationDataProvider()
            result = provider.get_per_percentile_in_5y_range(Ticker("7203"))

        assert result is None

    def test_returns_none_when_no_eps_data(self):
        mock_ticker = MagicMock()
        mock_ticker.info = {"trailingPE": 10.0}
        mock_ticker.history.return_value = _make_monthly_prices([100.0] * 12)
        financials_df = pd.DataFrame({"col": [0]}, index=["Other"])
        type(mock_ticker).financials = PropertyMock(return_value=financials_df)

        with patch("yfinance.Ticker", return_value=mock_ticker):
            provider = YFinanceEvaluationDataProvider()
            result = provider.get_per_percentile_in_5y_range(Ticker("7203"))

        assert result is None

    def test_returns_none_when_no_trailing_pe(self):
        mock_ticker = MagicMock()
        mock_ticker.info = {}
        mock_ticker.history.return_value = _make_monthly_prices([100.0] * 12)
        financials_df = pd.DataFrame({"col": [0]}, index=["Other"])
        type(mock_ticker).financials = PropertyMock(return_value=financials_df)

        with patch("yfinance.Ticker", return_value=mock_ticker):
            provider = YFinanceEvaluationDataProvider()
            result = provider.get_per_percentile_in_5y_range(Ticker("7203"))

        assert result is None
