from __future__ import annotations

import logging
from datetime import UTC, datetime

from stock_screener.discovery.domain.candidate import Candidate, ScreeningResult
from stock_screener.discovery.domain.hard_filter import HardFilter
from stock_screener.discovery.domain.scoring import CompositeScorer
from stock_screener.discovery.domain.scoring.percentile import PercentileCalculator
from stock_screener.discovery.domain.soft_filter import SoftFilter
from stock_screener.market_data.domain.security import Security
from stock_screener.shared.config import SCORING_MODE

logger = logging.getLogger(__name__)


class ScreeningService:
    """Screening service: hard filter -> soft filter -> scoring."""

    def __init__(
        self,
        hard_filter: HardFilter | None = None,
        soft_filter: SoftFilter | None = None,
    ) -> None:
        self._hard_filter = hard_filter or HardFilter()
        self._soft_filter = soft_filter or SoftFilter()

    def execute(self, securities: list[Security], top_n: int = 30) -> ScreeningResult:
        """Filter and score securities, return top N candidates."""
        total_universe = len(securities)
        logger.info("Universe: %d securities", total_universe)

        after_hard = self._hard_filter.apply(securities)
        logger.info("After hard filter: %d securities", len(after_hard))

        after_soft = self._soft_filter.apply(after_hard)
        logger.info("After soft filter: %d securities", len(after_soft))

        # Compute universe stats for hybrid mode
        universe_stats = None
        if SCORING_MODE == "hybrid":
            snapshots = [sec.financial_snapshot for sec in after_soft]
            universe_stats = PercentileCalculator.compute(snapshots)
            logger.info("Hybrid mode: computed universe stats from %d stocks", len(snapshots))

        scored = []
        for sec in after_soft:
            score = CompositeScorer.score(sec.financial_snapshot, universe_stats=universe_stats)
            scored.append((sec, score))

        scored.sort(key=lambda x: x[1].total, reverse=True)

        candidates = [Candidate(security=sec, score=score, rank=i + 1) for i, (sec, score) in enumerate(scored[:top_n])]

        return ScreeningResult(
            candidates=candidates,
            total_universe=total_universe,
            after_hard_filter=len(after_hard),
            after_soft_filter=len(after_soft),
            timestamp=datetime.now(tz=UTC),
        )
