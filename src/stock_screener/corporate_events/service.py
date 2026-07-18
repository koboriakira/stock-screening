from __future__ import annotations

from stock_screener.corporate_events.domain.earnings_date import EarningsDate
from stock_screener.corporate_events.domain.large_holding import LargeHoldingFiling
from stock_screener.corporate_events.infrastructure.jquants_earnings_provider import (
    JQuantsEarningsDateProvider,
)
from stock_screener.corporate_events.infrastructure.large_holding_provider import (
    EdinetLargeHoldingProvider,
)
from stock_screener.shared.types import Ticker


class LargeHoldingsService:
    """大量保有報告書(5%ルール)取得のアプリケーションサービス。"""

    def __init__(self, provider: EdinetLargeHoldingProvider) -> None:
        self._provider = provider

    def fetch(self, ticker: Ticker, days: int = 90) -> list[LargeHoldingFiling] | None:
        """指定銘柄の大量保有報告書を取得する。"""
        return self._provider.get_large_holdings(ticker, days=days)


class EarningsDateService:
    """決算発表予定日取得のアプリケーションサービス。"""

    def __init__(self, provider: JQuantsEarningsDateProvider) -> None:
        self._provider = provider

    def fetch(self, ticker: Ticker) -> EarningsDate | None:
        """指定銘柄の決算発表予定日を取得する。"""
        return self._provider.get_earnings_date(ticker)
