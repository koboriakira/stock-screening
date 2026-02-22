from __future__ import annotations

import logging

from stock_screener.market_data.domain.security import Security
from stock_screener.shared.config import HARD_FILTERS

logger = logging.getLogger(__name__)


class HardFilter:
    """Hard filter: exclude securities by absolute criteria.

    Filters by market cap range, minimum trading value, excluded sectors,
    and excluded market categories (ETF, REIT, etc.).
    """

    def __init__(
        self,
        market_cap_min: float = HARD_FILTERS["market_cap_min"],
        market_cap_max: float = HARD_FILTERS["market_cap_max"],
        avg_trading_value_min: float = HARD_FILTERS["avg_trading_value_min"],
        excluded_sectors: list[str] | None = None,
        excluded_categories: list[str] | None = None,
    ) -> None:
        self._market_cap_min = market_cap_min
        self._market_cap_max = market_cap_max
        self._avg_trading_value_min = avg_trading_value_min
        self._excluded_sectors = excluded_sectors or HARD_FILTERS["excluded_sectors"]
        self._excluded_categories = excluded_categories or HARD_FILTERS["excluded_categories"]

    def apply(self, securities: list[Security]) -> list[Security]:
        """Apply hard filters and return only passing securities."""
        return [s for s in securities if self._passes(s)]

    def _passes(self, security: Security) -> bool:
        snap = security.financial_snapshot

        if not self._check_market_cap(security, snap):
            return False

        if not self._check_trading_value(security, snap):
            return False

        if security.sector in self._excluded_sectors:
            logger.debug("%s: sector %s excluded", security.ticker, security.sector)
            return False

        if self._is_excluded_category(security.market):
            logger.debug("%s: market category %s excluded", security.ticker, security.market)
            return False

        return True

    def _check_market_cap(self, security: Security, snap: object) -> bool:
        if snap.market_cap is None:
            logger.debug("%s: market_cap is None, excluded", security.ticker)
            return False
        if not (self._market_cap_min <= snap.market_cap <= self._market_cap_max):
            logger.debug("%s: market_cap %s out of range", security.ticker, snap.market_cap)
            return False
        return True

    def _check_trading_value(self, security: Security, snap: object) -> bool:
        if snap.avg_trading_value is None:
            logger.debug("%s: avg_trading_value is None, excluded", security.ticker)
            return False
        if snap.avg_trading_value < self._avg_trading_value_min:
            logger.debug("%s: avg_trading_value %s too low", security.ticker, snap.avg_trading_value)
            return False
        return True

    def _is_excluded_category(self, market: str) -> bool:
        """Check if market category contains any excluded keyword."""
        if not market:
            return False
        return any(cat in market for cat in self._excluded_categories)
