from __future__ import annotations

from dataclasses import dataclass

from stock_screener.discovery.domain.scoring.momentum_score import MomentumScorer
from stock_screener.discovery.domain.scoring.percentile import UniverseStats
from stock_screener.discovery.domain.scoring.quality_score import QualityScorer
from stock_screener.discovery.domain.scoring.value_score import ValueScorer
from stock_screener.market_data.domain.financial_snapshot import FinancialSnapshot
from stock_screener.shared.config import (
    HYBRID_BASE_RATIO,
    SCORING_WEIGHTS,
    TURNAROUND_BONUS,
)


@dataclass(frozen=True)
class ScoreResult:
    """スコアリング結果。割安・質・変化の各スコアと加重合計を保持する。"""

    value: float
    quality: float
    momentum: float
    total: float


# カテゴリごとの指標と配点上限のマッピング
# (指標名, 配点上限, スナップショット属性名)
_VALUE_METRICS: list[tuple[str, float, str]] = [
    ("per", 25.0, "per"),
    ("pbr", 25.0, "pbr"),
    ("net_cash_ratio", 25.0, "net_cash_ratio"),
    ("high_52w_discount", 25.0, "high_52w_discount"),
]

_QUALITY_METRICS: list[tuple[str, float, str]] = [
    ("roe", 35.0, "roe"),
    ("operating_margin", 35.0, "operating_margin"),
    ("equity_ratio", 30.0, "equity_ratio"),
]

_MOMENTUM_METRICS: list[tuple[str, float, str]] = [
    ("revenue_growth", 35.0, "revenue_growth"),
    ("operating_profit_growth", 35.0, "operating_profit_growth"),
    ("dividend_yield", 30.0, "dividend_yield"),
]


def _hybrid_category_score(
    absolute_score: float,
    snap: FinancialSnapshot,
    metrics: list[tuple[str, float, str]],
    universe_stats: UniverseStats,
    base_ratio: float,
) -> float:
    """Compute hybrid score: base (absolute) + relative (percentile)."""
    relative_ratio = 1.0 - base_ratio

    # base points: absolute score * base_ratio
    base_points = absolute_score * base_ratio

    # relative points: percentile * max_score * relative_ratio
    total_max = sum(max_score for _, max_score, _ in metrics)
    relative_points = 0.0
    for metric_name, max_score, attr_name in metrics:
        value = getattr(snap, attr_name, None)
        pct = universe_stats.percentile(metric_name, value)
        relative_points += pct * max_score

    # 相対点を100点満点換算してからrelative_ratioをかける
    relative_normalized = (relative_points / total_max * 100) if total_max > 0 else 0.0
    relative_final = relative_normalized * relative_ratio

    return min(base_points + relative_final, 100.0)


class CompositeScorer:
    """割安・質・変化の3カテゴリで銘柄をスコアリングする複合スコアラ。"""

    @staticmethod
    def score(
        snap: FinancialSnapshot,
        *,
        prev_operating_profit_negative: bool = False,
        universe_stats: UniverseStats | None = None,
    ) -> ScoreResult:
        """財務スナップショットから加重スコアを算出する。

        When universe_stats is provided, use hybrid mode
        (base absolute + relative percentile). Otherwise use absolute mode.

        Adds turnaround bonus when prev operating profit was negative and current is positive.
        """
        # absolute scoring (legacy logic)
        value_raw = ValueScorer.score(snap)
        quality_raw = QualityScorer.score(snap)
        momentum_raw = MomentumScorer.score(snap)

        if universe_stats is not None:
            # ハイブリッドモード
            value_raw = _hybrid_category_score(
                value_raw,
                snap,
                _VALUE_METRICS,
                universe_stats,
                HYBRID_BASE_RATIO,
            )
            quality_raw = _hybrid_category_score(
                quality_raw,
                snap,
                _QUALITY_METRICS,
                universe_stats,
                HYBRID_BASE_RATIO,
            )
            momentum_raw = _hybrid_category_score(
                momentum_raw,
                snap,
                _MOMENTUM_METRICS,
                universe_stats,
                HYBRID_BASE_RATIO,
            )

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
            value=round(value_raw, 2),
            quality=round(quality_raw, 2),
            momentum=round(momentum_raw, 2),
            total=round(total, 2),
        )
