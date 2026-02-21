from __future__ import annotations

import logging

from stock_screener.market_data.domain.security import Security
from stock_screener.shared.config import SOFT_FILTERS

logger = logging.getLogger(__name__)


class SoftFilter:
    def __init__(
        self,
        per_max: float = SOFT_FILTERS["per_max"],
        equity_ratio_min: float = SOFT_FILTERS["equity_ratio_min"],
        revenue_growth_min: float = SOFT_FILTERS["revenue_growth_min"],
    ) -> None:
        self._per_max = per_max
        self._equity_ratio_min = equity_ratio_min
        self._revenue_growth_min = revenue_growth_min

    def apply(self, securities: list[Security]) -> list[Security]:
        return [s for s in securities if self._passes(s)]

    def _passes(self, security: Security) -> bool:
        snap = security.financial_snapshot

        if snap.per is not None and (snap.per < 0 or snap.per > self._per_max):
            logger.debug("%s: PER %s excluded", security.ticker, snap.per)
            return False

        if snap.equity_ratio is not None and snap.equity_ratio < self._equity_ratio_min:
            logger.debug("%s: equity_ratio %s too low", security.ticker, snap.equity_ratio)
            return False

        if snap.revenue_growth is not None and snap.revenue_growth < self._revenue_growth_min:
            logger.debug("%s: revenue_growth %s too low", security.ticker, snap.revenue_growth)
            return False

        return True
