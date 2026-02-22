from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

from stock_screener.discovery.domain.scoring import ScoreResult
from stock_screener.market_data.domain.security import Security

if TYPE_CHECKING:
    from stock_screener.discovery.domain.anomaly_detector import AnomalyFlag


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
    anomaly_flags: dict[str, list[AnomalyFlag]] = field(default_factory=dict)
