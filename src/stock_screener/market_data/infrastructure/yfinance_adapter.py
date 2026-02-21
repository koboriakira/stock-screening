from __future__ import annotations

import logging

import yfinance as yf

from stock_screener.market_data.domain.financial_snapshot import FinancialSnapshot
from stock_screener.market_data.domain.security import Security
from stock_screener.shared.types import Ticker

logger = logging.getLogger(__name__)


class YFinanceSecurityRepository:
    def get_universe(self) -> list[Security]:
        msg = "get_universe should be called via ScreeningService with JPX data"
        raise NotImplementedError(msg)

    def get_financial_snapshot(self, ticker: Ticker) -> FinancialSnapshot:
        try:
            info = yf.Ticker(ticker.symbol).info
        except Exception:
            logger.warning("Failed to fetch data for %s", ticker.symbol)
            return FinancialSnapshot()

        per = info.get("forwardPE") or info.get("trailingPE")
        pbr = info.get("priceToBook")
        roe = info.get("returnOnEquity")
        operating_margin = info.get("operatingMargins")
        revenue_growth = info.get("revenueGrowth")
        dividend_yield = info.get("dividendYield")
        market_cap = info.get("marketCap")
        current_price = info.get("currentPrice")
        fifty_two_week_high = info.get("fiftyTwoWeekHigh")
        average_volume = info.get("averageVolume")

        high_52w_discount = None
        if current_price and fifty_two_week_high and fifty_two_week_high > 0:
            high_52w_discount = (fifty_two_week_high - current_price) / fifty_two_week_high

        avg_trading_value = None
        if current_price and average_volume:
            avg_trading_value = current_price * average_volume

        return FinancialSnapshot(
            market_cap=market_cap,
            per=per,
            pbr=pbr,
            roe=roe,
            operating_margin=operating_margin,
            revenue_growth=revenue_growth,
            equity_ratio=None,
            dividend_yield=dividend_yield,
            high_52w_discount=high_52w_discount,
            net_cash_ratio=None,
            current_price=current_price,
            avg_trading_value=avg_trading_value,
        )
