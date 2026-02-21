from __future__ import annotations

import dataclasses
import logging

import pandas as pd
import yfinance as yf

from stock_screener.market_data.domain.financial_snapshot import FinancialSnapshot
from stock_screener.market_data.domain.security import Security
from stock_screener.market_data.infrastructure.cache import FileCache
from stock_screener.shared.types import Ticker

logger = logging.getLogger(__name__)


class YFinanceSecurityRepository:
    def __init__(self, cache: FileCache | None = None) -> None:
        self._cache = cache

    def get_universe(self) -> list[Security]:
        msg = "get_universe should be called via ScreeningService with JPX data"
        raise NotImplementedError(msg)

    def get_financial_snapshot(self, ticker: Ticker) -> FinancialSnapshot:
        cache_key = f"snapshot_{ticker.symbol}"
        if self._cache is not None:
            cached = self._cache.get(cache_key)
            if cached is not None:
                return FinancialSnapshot(**cached)

        snapshot = self._fetch_from_yfinance(ticker)

        if self._cache is not None:
            self._cache.set(cache_key, dataclasses.asdict(snapshot))

        return snapshot

    def _fetch_from_yfinance(self, ticker: Ticker) -> FinancialSnapshot:
        try:
            yf_ticker = yf.Ticker(ticker.symbol)
            info = yf_ticker.info
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

        total_cash = info.get("totalCash")
        total_debt = info.get("totalDebt")
        balance_sheet = _safe_get_dataframe(yf_ticker, "balance_sheet")
        financials = _safe_get_dataframe(yf_ticker, "financials")

        net_cash_ratio = _compute_net_cash_ratio(total_cash, total_debt, balance_sheet)
        equity_ratio = _compute_equity_ratio(balance_sheet)
        operating_profit_growth = _compute_operating_profit_growth(financials)

        return FinancialSnapshot(
            market_cap=market_cap,
            per=per,
            pbr=pbr,
            roe=roe,
            operating_margin=operating_margin,
            revenue_growth=revenue_growth,
            operating_profit_growth=operating_profit_growth,
            equity_ratio=equity_ratio,
            dividend_yield=dividend_yield,
            high_52w_discount=high_52w_discount,
            net_cash_ratio=net_cash_ratio,
            current_price=current_price,
            avg_trading_value=avg_trading_value,
        )


def _safe_get_dataframe(yf_ticker: yf.Ticker, attr: str) -> pd.DataFrame:
    try:
        df = getattr(yf_ticker, attr)
        if df is None:
            return pd.DataFrame()
        return df
    except Exception:
        return pd.DataFrame()


def _compute_net_cash_ratio(
    total_cash: float | None,
    total_debt: float | None,
    balance_sheet: pd.DataFrame,
) -> float | None:
    """net_cash_ratio = (totalCash - totalDebt) / totalAssets."""
    if total_cash is None or total_debt is None:
        return None
    total_assets = _get_balance_sheet_value(balance_sheet, "Total Assets")
    if total_assets is None or total_assets == 0:
        return None
    return (total_cash - total_debt) / total_assets


def _compute_equity_ratio(balance_sheet: pd.DataFrame) -> float | None:
    """equity_ratio = stockholdersEquity / totalAssets."""
    equity = _get_balance_sheet_value(balance_sheet, "Stockholders Equity")
    total_assets = _get_balance_sheet_value(balance_sheet, "Total Assets")
    if equity is None or total_assets is None or total_assets == 0:
        return None
    return equity / total_assets


def _compute_operating_profit_growth(financials: pd.DataFrame) -> float | None:
    """operating_profit_growth = (latest - previous) / |previous|."""
    if financials.empty or "Operating Income" not in financials.index:
        return None
    row = financials.loc["Operating Income"]
    if len(row) < 2:
        return None
    latest = row.iloc[0]
    previous = row.iloc[1]
    if previous == 0:
        return None
    return (latest - previous) / abs(previous)


def _get_balance_sheet_value(balance_sheet: pd.DataFrame, label: str) -> float | None:
    if balance_sheet.empty or label not in balance_sheet.index:
        return None
    value = balance_sheet.loc[label].iloc[0]
    if pd.isna(value):
        return None
    return float(value)
