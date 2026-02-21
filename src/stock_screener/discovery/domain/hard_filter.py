from __future__ import annotations

import logging

from stock_screener.market_data.domain.security import Security
from stock_screener.shared.config import HARD_FILTERS

logger = logging.getLogger(__name__)


class HardFilter:
    def __init__(
        self,
        market_cap_min: float = HARD_FILTERS["market_cap_min"],
        market_cap_max: float = HARD_FILTERS["market_cap_max"],
        avg_trading_value_min: float = HARD_FILTERS["avg_trading_value_min"],
        excluded_sectors: list[str] | None = None,
    ) -> None:
        self._market_cap_min = market_cap_min
        self._market_cap_max = market_cap_max
        self._avg_trading_value_min = avg_trading_value_min
        self._excluded_sectors = excluded_sectors or HARD_FILTERS["excluded_sectors"]

    def apply(self, securities: list[Security]) -> list[Security]:
        return [s for s in securities if self._passes(s)]

    def _passes(self, security: Security) -> bool:
        snap = security.financial_snapshot

        if snap.market_cap is None:
            logger.debug("%s: market_cap is None, excluded", security.ticker)
            return False
        if not (self._market_cap_min <= snap.market_cap <= self._market_cap_max):
            logger.debug("%s: market_cap %s out of range", security.ticker, snap.market_cap)
            return False

        if snap.avg_trading_value is None:
            logger.debug("%s: avg_trading_value is None, excluded", security.ticker)
            return False
        if snap.avg_trading_value < self._avg_trading_value_min:
            logger.debug("%s: avg_trading_value %s too low", security.ticker, snap.avg_trading_value)
            return False

        if security.sector in self._excluded_sectors:
            logger.debug("%s: sector %s excluded", security.ticker, security.sector)
            return False

        return True
