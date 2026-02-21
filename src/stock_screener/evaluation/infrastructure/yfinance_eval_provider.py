from __future__ import annotations

import logging

import yfinance as yf

from stock_screener.evaluation.infrastructure.stub_provider import StubEvaluationDataProvider
from stock_screener.shared.types import Ticker

logger = logging.getLogger(__name__)


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
