"""Tests for AnomalyDetector."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from stock_screener.discovery.domain.anomaly_detector import AnomalyDetector, AnomalyFlag
from stock_screener.discovery.domain.candidate import Candidate
from stock_screener.discovery.domain.diff_report import CandidateSnapshot, ScreeningResultSnapshot
from stock_screener.discovery.domain.scoring import ScoreResult
from stock_screener.market_data.domain.financial_snapshot import FinancialSnapshot
from stock_screener.market_data.domain.security import Security
from stock_screener.shared.types import Ticker


def _make_snapshot(**kwargs: float | None) -> FinancialSnapshot:
    """Create a FinancialSnapshot with specified overrides."""
    defaults: dict[str, float | None] = {
        "market_cap": 10_000_000_000,
        "per": 10.0,
        "pbr": 1.0,
        "roe": 0.10,
        "operating_margin": 0.10,
        "revenue_growth": 0.05,
        "operating_profit_growth": 0.10,
        "equity_ratio": 0.50,
        "dividend_yield": 3.0,
        "high_52w_discount": 0.10,
        "net_cash_ratio": 0.30,
        "current_price": 1000.0,
        "avg_trading_value": 10_000_000,
    }
    defaults.update(kwargs)
    return FinancialSnapshot(**defaults)


class TestAnomalyFlag:
    """AnomalyFlag value object tests."""

    def test_create_flag(self) -> None:
        flag = AnomalyFlag(field="pbr", value=0.002, rule="domain_range", detail="PBR 0.002 < min 0.05")
        assert flag.field == "pbr"
        assert flag.value == 0.002
        assert flag.rule == "domain_range"
        assert flag.detail == "PBR 0.002 < min 0.05"

    def test_is_frozen(self) -> None:
        flag = AnomalyFlag(field="pbr", value=0.002, rule="domain_range", detail="test")
        with pytest.raises(AttributeError):
            flag.field = "per"  # type: ignore[misc]


class TestDomainRuleDetection:
    """Tests for domain knowledge range checks (Rule 2)."""

    def test_normal_values_no_flags(self) -> None:
        """Normal financial values should produce no anomaly flags."""
        snapshot = _make_snapshot()
        detector = AnomalyDetector()
        flags = detector.check_domain_rules(snapshot)
        assert flags == []

    def test_pbr_too_low(self) -> None:
        """PBR below 0.05 should be flagged."""
        snapshot = _make_snapshot(pbr=0.002)
        detector = AnomalyDetector()
        flags = detector.check_domain_rules(snapshot)
        assert len(flags) == 1
        assert flags[0].field == "pbr"
        assert flags[0].rule == "domain_range"
        assert "0.05" in flags[0].detail

    def test_pbr_too_high(self) -> None:
        """PBR above 50.0 should be flagged."""
        snapshot = _make_snapshot(pbr=55.0)
        detector = AnomalyDetector()
        flags = detector.check_domain_rules(snapshot)
        assert len(flags) == 1
        assert flags[0].field == "pbr"

    def test_per_too_low(self) -> None:
        """PER below 0.1 should be flagged."""
        snapshot = _make_snapshot(per=0.05)
        detector = AnomalyDetector()
        flags = detector.check_domain_rules(snapshot)
        assert len(flags) == 1
        assert flags[0].field == "per"

    def test_per_too_high(self) -> None:
        """PER above 200 should be flagged."""
        snapshot = _make_snapshot(per=250.0)
        detector = AnomalyDetector()
        flags = detector.check_domain_rules(snapshot)
        assert len(flags) == 1
        assert flags[0].field == "per"

    def test_roe_out_of_range(self) -> None:
        """ROE outside -100%~100% should be flagged."""
        snapshot = _make_snapshot(roe=1.5)
        detector = AnomalyDetector()
        flags = detector.check_domain_rules(snapshot)
        assert len(flags) == 1
        assert flags[0].field == "roe"

    def test_dividend_yield_too_high(self) -> None:
        """Dividend yield above 20% should be flagged."""
        snapshot = _make_snapshot(dividend_yield=25.0)
        detector = AnomalyDetector()
        flags = detector.check_domain_rules(snapshot)
        assert len(flags) == 1
        assert flags[0].field == "dividend_yield"

    def test_multiple_anomalies(self) -> None:
        """Multiple anomalous values should produce multiple flags."""
        snapshot = _make_snapshot(pbr=0.002, per=0.05, roe=2.0)
        detector = AnomalyDetector()
        flags = detector.check_domain_rules(snapshot)
        assert len(flags) == 3
        flagged_fields = {f.field for f in flags}
        assert flagged_fields == {"pbr", "per", "roe"}

    def test_none_values_skipped(self) -> None:
        """None values should not produce flags."""
        snapshot = _make_snapshot(pbr=None, per=None)
        detector = AnomalyDetector()
        flags = detector.check_domain_rules(snapshot)
        assert flags == []

    def test_boundary_values_not_flagged(self) -> None:
        """Values exactly at boundaries should not be flagged."""
        snapshot = _make_snapshot(pbr=0.05, per=0.1, roe=1.0, dividend_yield=20.0)
        detector = AnomalyDetector()
        flags = detector.check_domain_rules(snapshot)
        assert flags == []

    def test_net_cash_ratio_out_of_range(self) -> None:
        """Net cash ratio outside -200%~500% should be flagged."""
        snapshot = _make_snapshot(net_cash_ratio=6.0)
        detector = AnomalyDetector()
        flags = detector.check_domain_rules(snapshot)
        assert len(flags) == 1
        assert flags[0].field == "net_cash_ratio"

    def test_operating_margin_out_of_range(self) -> None:
        """Operating margin outside -100%~100% should be flagged."""
        snapshot = _make_snapshot(operating_margin=-1.5)
        detector = AnomalyDetector()
        flags = detector.check_domain_rules(snapshot)
        assert len(flags) == 1
        assert flags[0].field == "operating_margin"

    def test_equity_ratio_out_of_range(self) -> None:
        """Equity ratio outside 0~100% should be flagged."""
        snapshot = _make_snapshot(equity_ratio=-0.1)
        detector = AnomalyDetector()
        flags = detector.check_domain_rules(snapshot)
        assert len(flags) == 1
        assert flags[0].field == "equity_ratio"

    def test_op_profit_growth_extreme_high(self) -> None:
        """営業利益成長率が+500%を超える場合はフラグ。"""
        snapshot = _make_snapshot(operating_profit_growth=15.0)
        detector = AnomalyDetector()
        flags = detector.check_domain_rules(snapshot)
        growth_flags = [f for f in flags if f.field == "operating_profit_growth"]
        assert len(growth_flags) == 1

    def test_op_profit_growth_extreme_low(self) -> None:
        """営業利益成長率が-95%を下回る場合はフラグ。"""
        snapshot = _make_snapshot(operating_profit_growth=-0.98)
        detector = AnomalyDetector()
        flags = detector.check_domain_rules(snapshot)
        growth_flags = [f for f in flags if f.field == "operating_profit_growth"]
        assert len(growth_flags) == 1

    def test_op_profit_growth_normal_no_flag(self) -> None:
        """営業利益成長率が正常範囲ならフラグなし。"""
        snapshot = _make_snapshot(operating_profit_growth=0.25)
        detector = AnomalyDetector()
        flags = detector.check_domain_rules(snapshot)
        growth_flags = [f for f in flags if f.field == "operating_profit_growth"]
        assert growth_flags == []

    def test_revenue_growth_extreme_high(self) -> None:
        """売上高成長率が+500%を超える場合はフラグ。"""
        snapshot = _make_snapshot(revenue_growth=6.0)
        detector = AnomalyDetector()
        flags = detector.check_domain_rules(snapshot)
        growth_flags = [f for f in flags if f.field == "revenue_growth"]
        assert len(growth_flags) == 1


class TestIqrOutlierDetection:
    """Tests for IQR-based outlier detection (Rule 1)."""

    def _make_snapshots(self, per_values: list[float]) -> list[FinancialSnapshot]:
        return [_make_snapshot(per=v) for v in per_values]

    def test_normal_distribution_no_flags(self) -> None:
        """Values within IQR bounds should not be flagged."""
        # 10 normal PER values around 10-15
        values = [10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 11.5, 12.5, 13.5, 14.5]
        snapshots = self._make_snapshots(values)
        detector = AnomalyDetector()
        target = _make_snapshot(per=12.0)
        flags = detector.check_iqr_outliers(target, snapshots)
        assert flags == []

    def test_extreme_outlier_flagged(self) -> None:
        """An extreme outlier should be flagged."""
        # Normal values: 10-15, then a target with PER=200
        values = [10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 11.5, 12.5, 13.5, 14.5]
        snapshots = self._make_snapshots(values)
        detector = AnomalyDetector()
        target = _make_snapshot(per=200.0)
        flags = detector.check_iqr_outliers(target, snapshots)
        per_flags = [f for f in flags if f.field == "per"]
        assert len(per_flags) == 1
        assert per_flags[0].rule == "iqr_outlier"

    def test_low_outlier_flagged(self) -> None:
        """A very low outlier should be flagged."""
        values = [10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 11.5, 12.5, 13.5, 14.5]
        snapshots = self._make_snapshots(values)
        detector = AnomalyDetector()
        target = _make_snapshot(per=0.01)
        flags = detector.check_iqr_outliers(target, snapshots)
        per_flags = [f for f in flags if f.field == "per"]
        assert len(per_flags) == 1

    def test_none_values_skipped(self) -> None:
        """None values in universe should be skipped."""
        snapshots = [_make_snapshot(per=None) for _ in range(5)]
        detector = AnomalyDetector()
        target = _make_snapshot(per=10.0)
        flags = detector.check_iqr_outliers(target, snapshots)
        # Not enough data to compute IQR, so no flags
        assert flags == []

    def test_target_none_skipped(self) -> None:
        """None value in target should not produce flags for that field."""
        values = [10.0, 11.0, 12.0, 13.0, 14.0]
        snapshots = self._make_snapshots(values)
        detector = AnomalyDetector()
        target = _make_snapshot(per=None)
        flags = detector.check_iqr_outliers(target, snapshots)
        per_flags = [f for f in flags if f.field == "per"]
        assert per_flags == []

    def test_insufficient_data_no_flags(self) -> None:
        """With too few data points, IQR cannot be computed reliably."""
        snapshots = [_make_snapshot(per=10.0)]
        detector = AnomalyDetector()
        target = _make_snapshot(per=100.0)
        flags = detector.check_iqr_outliers(target, snapshots)
        per_flags = [f for f in flags if f.field == "per"]
        assert per_flags == []

    def test_multiple_fields_checked(self) -> None:
        """IQR check should cover multiple fields."""
        # Create universe with normal PBR values
        snapshots = [_make_snapshot(pbr=v) for v in [0.8, 0.9, 1.0, 1.1, 1.2, 1.0, 0.9, 1.1, 0.95, 1.05]]
        detector = AnomalyDetector()
        target = _make_snapshot(pbr=50.0)  # extreme outlier
        flags = detector.check_iqr_outliers(target, snapshots)
        pbr_flags = [f for f in flags if f.field == "pbr"]
        assert len(pbr_flags) == 1


def _make_prev_snapshot(candidates: list[tuple[str, str, float]]) -> ScreeningResultSnapshot:
    """Create a previous ScreeningResultSnapshot from (ticker, name, score) tuples."""
    snaps = [
        CandidateSnapshot(
            ticker=t, name=n, score_total=s,
            score_value=s * 0.4, score_quality=s * 0.3, score_momentum=s * 0.3,
            rank=i + 1,
        )
        for i, (t, n, s) in enumerate(candidates)
    ]
    return ScreeningResultSnapshot(
        execution_date=datetime(2026, 2, 21, tzinfo=UTC),
        universe_size=100,
        hard_filter_passed=80,
        soft_filter_passed=60,
        candidates=snaps,
    )


class TestScoreChangeDetection:
    """Tests for score change detection (Rule 3)."""

    def test_no_previous_snapshot_no_flags(self) -> None:
        """With no previous snapshot, no flags should be generated."""
        detector = AnomalyDetector()
        result = detector.check_score_changes(
            {"1234.T": 80.0, "5678.T": 70.0},
            previous=None,
        )
        assert result == {}

    def test_no_change_no_flags(self) -> None:
        """Stable scores should produce no flags."""
        prev = _make_prev_snapshot([("1234.T", "TestCo", 80.0)])
        detector = AnomalyDetector()
        result = detector.check_score_changes(
            {"1234.T": 80.0},
            previous=prev,
        )
        assert result == {}

    def test_small_change_no_flags(self) -> None:
        """Score changes below threshold should not be flagged."""
        prev = _make_prev_snapshot([("1234.T", "TestCo", 80.0)])
        detector = AnomalyDetector()
        result = detector.check_score_changes(
            {"1234.T": 85.0},
            previous=prev,
        )
        assert result == {}

    def test_large_increase_flagged(self) -> None:
        """Score increase >= 20 points should be flagged."""
        prev = _make_prev_snapshot([("1234.T", "TestCo", 50.0)])
        detector = AnomalyDetector()
        result = detector.check_score_changes(
            {"1234.T": 80.0},
            previous=prev,
        )
        assert "1234.T" in result
        assert len(result["1234.T"]) == 1
        assert result["1234.T"][0].rule == "score_change"

    def test_large_decrease_flagged(self) -> None:
        """Score decrease >= 20 points should be flagged."""
        prev = _make_prev_snapshot([("1234.T", "TestCo", 80.0)])
        detector = AnomalyDetector()
        result = detector.check_score_changes(
            {"1234.T": 55.0},
            previous=prev,
        )
        assert "1234.T" in result
        assert len(result["1234.T"]) == 1

    def test_new_ticker_not_flagged(self) -> None:
        """New tickers not in previous snapshot should not be flagged."""
        prev = _make_prev_snapshot([("1234.T", "TestCo", 80.0)])
        detector = AnomalyDetector()
        result = detector.check_score_changes(
            {"9999.T": 50.0},
            previous=prev,
        )
        assert result == {}

    def test_boundary_not_flagged(self) -> None:
        """Score change exactly at threshold (19.9) should not be flagged."""
        prev = _make_prev_snapshot([("1234.T", "TestCo", 50.0)])
        detector = AnomalyDetector()
        result = detector.check_score_changes(
            {"1234.T": 69.9},
            previous=prev,
        )
        assert result == {}


def _make_candidate(ticker: str, score: float, **snap_kwargs: float | None) -> Candidate:
    """Create a Candidate with the given ticker, score, and snapshot overrides."""
    snap = _make_snapshot(**snap_kwargs)
    security = Security(
        ticker=Ticker(ticker),
        company_name="TestCo",
        sector="情報・通信業",
        market=None,
    )
    security.financial_snapshot = snap
    return Candidate(
        security=security,
        score=ScoreResult(value=score * 0.4, quality=score * 0.3, momentum=score * 0.3, total=score),
        rank=1,
    )


class TestDetectAll:
    """Tests for detect_all integration method."""

    def test_no_anomalies(self) -> None:
        """Normal candidates should produce empty dict."""
        candidate = _make_candidate("1234.T", 80.0)
        detector = AnomalyDetector()
        result = detector.detect_all([candidate], [_make_snapshot()])
        assert result == {}

    def test_domain_rule_detected(self) -> None:
        """Domain rule anomaly should be included."""
        candidate = _make_candidate("1234.T", 80.0, pbr=0.002)
        detector = AnomalyDetector()
        result = detector.detect_all([candidate], [_make_snapshot()])
        assert "1234.T" in result
        assert any(f.rule == "domain_range" for f in result["1234.T"])

    def test_iqr_and_domain_merged(self) -> None:
        """IQR and domain flags should be merged for same ticker."""
        universe = [_make_snapshot(pbr=v) for v in [0.8, 0.9, 1.0, 1.1, 1.2, 1.0, 0.9, 1.1, 0.95, 1.05]]
        candidate = _make_candidate("1234.T", 80.0, pbr=0.002)
        detector = AnomalyDetector()
        result = detector.detect_all([candidate], universe)
        assert "1234.T" in result
        rules = {f.rule for f in result["1234.T"]}
        assert "domain_range" in rules
        assert "iqr_outlier" in rules

    def test_score_change_included(self) -> None:
        """Score change flags should be included."""
        prev = _make_prev_snapshot([("1234.T", "TestCo", 50.0)])
        candidate = _make_candidate("1234.T", 80.0)
        detector = AnomalyDetector()
        result = detector.detect_all([candidate], [_make_snapshot()], previous=prev)
        assert "1234.T" in result
        assert any(f.rule == "score_change" for f in result["1234.T"])
