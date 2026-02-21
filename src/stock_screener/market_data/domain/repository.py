from __future__ import annotations

from typing import Protocol

from stock_screener.market_data.domain.financial_snapshot import FinancialSnapshot
from stock_screener.market_data.domain.security import Security
from stock_screener.shared.types import Ticker


class SecurityRepository(Protocol):
    def get_universe(self) -> list[Security]:
        """JPX銘柄リストから全銘柄のSecurity一覧を取得する"""
        ...

    def get_financial_snapshot(self, ticker: Ticker) -> FinancialSnapshot:
        """指定ティッカーの財務スナップショットを取得する"""
        ...
