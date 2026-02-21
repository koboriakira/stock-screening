from __future__ import annotations

import logging

import pandas as pd
import yfinance as yf

from stock_screener.evaluation.infrastructure.stub_provider import StubEvaluationDataProvider
from stock_screener.shared.types import Ticker

logger = logging.getLogger(__name__)


def compute_per_percentile(
    monthly_prices: pd.DataFrame,
    eps_series: pd.Series,
    current_per: float,
) -> float | None:
    if monthly_prices.empty or eps_series.empty:
        return None

    eps_sorted = eps_series.sort_index()
    positive_eps = eps_sorted[eps_sorted > 0]
    if positive_eps.empty:
        return None

    # タイムゾーン統一: 両方tz-naiveにする
    if hasattr(monthly_prices.index, "tz") and monthly_prices.index.tz is not None:
        monthly_prices = monthly_prices.copy()
        monthly_prices.index = monthly_prices.index.tz_localize(None)
    if hasattr(positive_eps.index, "tz") and positive_eps.index.tz is not None:
        positive_eps = positive_eps.copy()
        positive_eps.index = positive_eps.index.tz_localize(None)

    historical_pers: list[float] = []
    for date, row in monthly_prices.iterrows():
        price = row["Close"]
        if price is None or price <= 0:
            continue
        applicable_eps = positive_eps[positive_eps.index <= date]
        if applicable_eps.empty:
            continue
        eps = applicable_eps.iloc[-1]
        per = price / eps
        if per > 0:
            historical_pers.append(per)

    if len(historical_pers) < 6:
        return None

    count_below = sum(1 for p in historical_pers if p <= current_per)
    return 100.0 * count_below / len(historical_pers)


class YFinanceEvaluationDataProvider(StubEvaluationDataProvider):
    def get_earnings_growth_forecast(self, ticker: Ticker) -> float | None:
        try:
            info = yf.Ticker(ticker.symbol).info
        except Exception:
            logger.warning("Failed to fetch earningsGrowth for %s", ticker.symbol)
            return None
        value = info.get("earningsGrowth")
        if value is None:
            return None
        return float(value)

    def get_per_percentile_in_5y_range(self, ticker: Ticker) -> float | None:
        try:
            yf_ticker = yf.Ticker(ticker.symbol)
            info = yf_ticker.info
            current_per = info.get("trailingPE") or info.get("forwardPE")
            if current_per is None:
                return None

            history = yf_ticker.history(period="5y", interval="1mo")
            if history.empty:
                return None

            financials = yf_ticker.financials
            if financials is None or financials.empty:
                return None
            if "Diluted EPS" not in financials.index:
                return None

            eps_series = financials.loc["Diluted EPS"].dropna()
            return compute_per_percentile(history, eps_series, float(current_per))
        except Exception:
            logger.warning("Failed to fetch PER percentile for %s", ticker.symbol)
            return None
