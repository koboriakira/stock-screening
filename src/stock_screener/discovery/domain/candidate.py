from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from stock_screener.discovery.domain.scoring import ScoreResult
from stock_screener.market_data.domain.security import Security


@dataclass(frozen=True)
class Candidate:
    security: Security
    score: ScoreResult
    rank: int


@dataclass(frozen=True)
class ScreeningResult:
    candidates: list[Candidate]
    total_universe: int
    after_hard_filter: int
    after_soft_filter: int
    timestamp: datetime
