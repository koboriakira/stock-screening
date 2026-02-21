from __future__ import annotations

from dataclasses import dataclass

from stock_screener.discovery.domain.scoring.momentum_score import MomentumScorer
from stock_screener.discovery.domain.scoring.quality_score import QualityScorer
from stock_screener.discovery.domain.scoring.value_score import ValueScorer
from stock_screener.market_data.domain.financial_snapshot import FinancialSnapshot
from stock_screener.shared.config import SCORING_WEIGHTS, TURNAROUND_BONUS


@dataclass(frozen=True)
class ScoreResult:
    """スコアリング結果。割安・質・変化の各スコアと加重合計を保持する。"""

    value: float
    quality: float
    momentum: float
    total: float


class CompositeScorer:
    """割安・質・変化の3カテゴリで銘柄をスコアリングする複合スコアラ。"""

    @staticmethod
    def score(snap: FinancialSnapshot, *, prev_operating_profit_negative: bool = False) -> ScoreResult:
        """財務スナップショットから加重スコアを算出する。

        前期営業利益が赤字かつ今期黒字転換の場合、ターンアラウンドボーナスを加算する。
        """
        value_raw = ValueScorer.score(snap)
        quality_raw = QualityScorer.score(snap)
        momentum_raw = MomentumScorer.score(snap)

        total = (
            value_raw * SCORING_WEIGHTS["value"]
            + quality_raw * SCORING_WEIGHTS["quality"]
            + momentum_raw * SCORING_WEIGHTS["momentum"]
        )

        if (
            prev_operating_profit_negative
            and snap.operating_profit_growth is not None
            and snap.operating_profit_growth > 0
        ):
            total += TURNAROUND_BONUS

        total = min(total, 100)

        return ScoreResult(
            value=value_raw,
            quality=quality_raw,
            momentum=momentum_raw,
            total=round(total, 2),
        )
