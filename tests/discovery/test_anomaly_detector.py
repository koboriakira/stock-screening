"""Tests for AnomalyDetector domain rules."""

from __future__ import annotations

import pytest

from stock_screener.discovery.domain.anomaly_detector import AnomalyDetector, AnomalyFlag
from stock_screener.market_data.domain.financial_snapshot import FinancialSnapshot


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
        "dividend_yield": 0.03,
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
        snapshot = _make_snapshot(dividend_yield=0.25)
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
        snapshot = _make_snapshot(pbr=0.05, per=0.1, roe=1.0, dividend_yield=0.20)
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
