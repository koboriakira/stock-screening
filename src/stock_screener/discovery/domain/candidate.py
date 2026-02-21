from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from stock_screener.discovery.domain.scoring import ScoreResult
from stock_screener.market_data.domain.security import Security


@dataclass(frozen=True)
class Candidate:
    """スクリーニング通過後の候補銘柄。スコアと順位を保持する。"""

    security: Security
    score: ScoreResult
    rank: int


@dataclass(frozen=True)
class ScreeningResult:
    """スクリーニング実行結果。候補銘柄リストとフィルタリング統計を保持する。"""

    candidates: list[Candidate]
    total_universe: int
    after_hard_filter: int
    after_soft_filter: int
    timestamp: datetime
