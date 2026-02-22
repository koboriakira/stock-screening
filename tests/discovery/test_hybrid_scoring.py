"""Tests for hybrid scoring mode.

Base points (absolute 40%) + relative points (percentile 60%)
to resolve score saturation.
"""

from stock_screener.discovery.domain.scoring import CompositeScorer
from stock_screener.discovery.domain.scoring.percentile import (
    PercentileCalculator,
    UniverseStats,
)
from stock_screener.market_data.domain.financial_snapshot import FinancialSnapshot


class TestPercentileCalculator:
    """Percentile calculation for universe."""

    def test_compute_from_snapshots(self):
        """Compute percentiles from multiple snapshots."""
        snaps = [
            FinancialSnapshot(roe=0.02),
            FinancialSnapshot(roe=0.05),
            FinancialSnapshot(roe=0.08),
            FinancialSnapshot(roe=0.12),
            FinancialSnapshot(roe=0.20),
        ]
        stats = PercentileCalculator.compute(snaps)
        assert isinstance(stats, UniverseStats)

    def test_percentile_for_roe(self):
        """ROE percentile: higher ROE = higher percentile."""
        snaps = [
            FinancialSnapshot(roe=0.02),
            FinancialSnapshot(roe=0.05),
            FinancialSnapshot(roe=0.08),
            FinancialSnapshot(roe=0.12),
            FinancialSnapshot(roe=0.20),
        ]
        stats = PercentileCalculator.compute(snaps)
        p_high = stats.percentile("roe", 0.20)
        p_low = stats.percentile("roe", 0.02)
        assert p_high > p_low

    def test_percentile_for_per_is_inverted(self):
        """PER percentile: lower PER = higher percentile (cheaper = better)."""
        snaps = [
            FinancialSnapshot(per=5.0),
            FinancialSnapshot(per=10.0),
            FinancialSnapshot(per=15.0),
            FinancialSnapshot(per=20.0),
            FinancialSnapshot(per=30.0),
        ]
        stats = PercentileCalculator.compute(snaps)
        p_low_per = stats.percentile("per", 5.0)
        p_high_per = stats.percentile("per", 30.0)
        # lower PER should have higher percentile (cheaper)
        assert p_low_per > p_high_per

    def test_percentile_none_returns_zero(self):
        """None value returns 0 percentile."""
        snaps = [
            FinancialSnapshot(roe=0.05),
            FinancialSnapshot(roe=0.10),
        ]
        stats = PercentileCalculator.compute(snaps)
        assert stats.percentile("roe", None) == 0.0

    def test_empty_universe_returns_zero(self):
        """Empty universe returns 0 percentile."""
        stats = PercentileCalculator.compute([])
        assert stats.percentile("roe", 0.10) == 0.0


class TestHybridCompositeScorer:
    """Hybrid mode CompositeScorer tests."""

    def _make_universe(self) -> list[FinancialSnapshot]:
        """Test universe with varying quality metrics."""
        return [
            FinancialSnapshot(
                roe=0.02,
                operating_margin=0.03,
                equity_ratio=0.25,
                per=25.0,
                pbr=1.8,
            ),
            FinancialSnapshot(
                roe=0.05,
                operating_margin=0.06,
                equity_ratio=0.35,
                per=15.0,
                pbr=1.2,
            ),
            FinancialSnapshot(
                roe=0.08,
                operating_margin=0.10,
                equity_ratio=0.50,
                per=10.0,
                pbr=0.8,
            ),
            FinancialSnapshot(
                roe=0.12,
                operating_margin=0.15,
                equity_ratio=0.60,
                per=7.0,
                pbr=0.6,
            ),
            FinancialSnapshot(
                roe=0.20,
                operating_margin=0.20,
                equity_ratio=0.70,
                per=5.0,
                pbr=0.5,
            ),
        ]

    def test_hybrid_quality_scores_not_saturated(self):
        """In hybrid mode, quality score 100 stocks should be <= 20%."""
        universe = self._make_universe()
        stats = PercentileCalculator.compute(universe)

        scores = []
        for snap in universe:
            result = CompositeScorer.score(snap, universe_stats=stats)
            scores.append(result.quality)

        # at most 1 out of 5 stocks can have perfect score
        perfect_count = sum(1 for s in scores if s >= 99.9)
        assert perfect_count <= 1, f"saturated: {perfect_count} stocks at 100"

    def test_hybrid_differentiates_high_quality_stocks(self):
        """Stocks equal in absolute score are differentiated in hybrid mode."""
        universe = self._make_universe()
        stats = PercentileCalculator.compute(universe)

        # ROE 8% and 20% both score 35 in absolute mode,
        # but hybrid should rank ROE 20% higher
        snap_8pct = universe[2]  # ROE 0.08
        snap_20pct = universe[4]  # ROE 0.20

        result_8 = CompositeScorer.score(snap_8pct, universe_stats=stats)
        result_20 = CompositeScorer.score(snap_20pct, universe_stats=stats)

        assert result_20.quality > result_8.quality

    def test_absolute_mode_backward_compatible(self):
        """universe_stats=None falls back to absolute mode."""
        snap = FinancialSnapshot(
            per=5.0,
            pbr=0.5,
            net_cash_ratio=0.5,
            high_52w_discount=0.3,
            roe=0.08,
            operating_margin=0.10,
            equity_ratio=0.50,
            revenue_growth=0.20,
            operating_profit_growth=0.30,
            dividend_yield=0.04,
        )
        result = CompositeScorer.score(snap, universe_stats=None)
        # absolute: value=100*0.4 + quality=100*0.3 + momentum=100*0.3 = 100
        assert result.total == 100

    def test_hybrid_total_within_range(self):
        """Hybrid mode scores are within 0-100 range."""
        universe = self._make_universe()
        stats = PercentileCalculator.compute(universe)

        for snap in universe:
            result = CompositeScorer.score(snap, universe_stats=stats)
            assert 0 <= result.total <= 100
            assert 0 <= result.value <= 100
            assert 0 <= result.quality <= 100
            assert 0 <= result.momentum <= 100
