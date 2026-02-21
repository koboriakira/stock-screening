from __future__ import annotations

from stock_screener.evaluation.domain.check import CheckStatus
from stock_screener.evaluation.domain.evaluation_target import EvaluationTarget
from stock_screener.evaluation.domain.gate2_catalyst import CatalystGate
from stock_screener.market_data.domain.financial_snapshot import FinancialSnapshot
from stock_screener.shared.types import Ticker


def _make_target(**kwargs) -> EvaluationTarget:
    defaults = {
        "ticker": Ticker("1234"),
        "company_name": "テスト株",
        "sector": "電気機器",
        "financial_snapshot": FinancialSnapshot(),
        "discovery_rank": 1,
        "score_total": 50.0,
    }
    defaults.update(kwargs)
    return EvaluationTarget(**defaults)


class StubProvider:
    def check_accounting_fraud(self, ticker: Ticker) -> CheckStatus:
        return CheckStatus.NEEDS_REVIEW

    def check_going_concern(self, ticker: Ticker) -> CheckStatus:
        return CheckStatus.NEEDS_REVIEW

    def get_margin_trading_ratio(self, ticker: Ticker) -> float | None:
        return None

    def get_earnings_growth_forecast(self, ticker: Ticker) -> float | None:
        return None

    def get_quarterly_progress_improvement(self, ticker: Ticker) -> float | None:
        return None

    def has_upward_revision(self, ticker: Ticker) -> bool | None:
        return None

    def has_share_buyback(self, ticker: Ticker) -> bool | None:
        return None

    def get_per_percentile_in_5y_range(self, ticker: Ticker) -> float | None:
        return None


class EarningsGrowthProvider(StubProvider):
    def __init__(self, growth: float | None):
        self._growth = growth

    def get_earnings_growth_forecast(self, ticker: Ticker) -> float | None:
        return self._growth


class TestCheck2A2EarningsGrowth:
    def test_above_20_passes(self):
        gate = CatalystGate()
        target = _make_target(financial_snapshot=FinancialSnapshot())
        result = gate.evaluate(target, EarningsGrowthProvider(0.25))
        check = next(c for c in result.checks if c.check_id == "2A-2")
        assert check.status == CheckStatus.PASS

    def test_below_20_fails(self):
        gate = CatalystGate()
        result = gate.evaluate(_make_target(), EarningsGrowthProvider(0.10))
        check = next(c for c in result.checks if c.check_id == "2A-2")
        assert check.status == CheckStatus.FAIL

    def test_exactly_20_passes(self):
        gate = CatalystGate()
        result = gate.evaluate(_make_target(), EarningsGrowthProvider(0.20))
        check = next(c for c in result.checks if c.check_id == "2A-2")
        assert check.status == CheckStatus.PASS

    def test_none_needs_review(self):
        gate = CatalystGate()
        result = gate.evaluate(_make_target(), EarningsGrowthProvider(None))
        check = next(c for c in result.checks if c.check_id == "2A-2")
        assert check.status == CheckStatus.NEEDS_REVIEW


class TestCheck2D2TobMbo:
    def test_pbr_low_net_cash_high_passes(self):
        gate = CatalystGate()
        target = _make_target(financial_snapshot=FinancialSnapshot(pbr=0.7, net_cash_ratio=0.35))
        result = gate.evaluate(target, StubProvider())
        check = next(c for c in result.checks if c.check_id == "2D-2")
        assert check.status == CheckStatus.PASS

    def test_pbr_above_1_fails(self):
        gate = CatalystGate()
        target = _make_target(financial_snapshot=FinancialSnapshot(pbr=1.2, net_cash_ratio=0.35))
        result = gate.evaluate(target, StubProvider())
        check = next(c for c in result.checks if c.check_id == "2D-2")
        assert check.status == CheckStatus.FAIL

    def test_net_cash_below_30_fails(self):
        gate = CatalystGate()
        target = _make_target(financial_snapshot=FinancialSnapshot(pbr=0.7, net_cash_ratio=0.20))
        result = gate.evaluate(target, StubProvider())
        check = next(c for c in result.checks if c.check_id == "2D-2")
        assert check.status == CheckStatus.FAIL

    def test_missing_data_needs_review(self):
        gate = CatalystGate()
        target = _make_target(financial_snapshot=FinancialSnapshot())
        result = gate.evaluate(target, StubProvider())
        check = next(c for c in result.checks if c.check_id == "2D-2")
        assert check.status == CheckStatus.NEEDS_REVIEW


class TestStubChecks:
    def test_2a1_stub_returns_needs_review(self):
        gate = CatalystGate()
        result = gate.evaluate(_make_target(), StubProvider())
        check = next(c for c in result.checks if c.check_id == "2A-1")
        assert check.status == CheckStatus.NEEDS_REVIEW

    def test_2a3_stub_returns_needs_review(self):
        gate = CatalystGate()
        result = gate.evaluate(_make_target(), StubProvider())
        check = next(c for c in result.checks if c.check_id == "2A-3")
        assert check.status == CheckStatus.NEEDS_REVIEW

    def test_2b2_stub_returns_needs_review(self):
        gate = CatalystGate()
        result = gate.evaluate(_make_target(), StubProvider())
        check = next(c for c in result.checks if c.check_id == "2B-2")
        assert check.status == CheckStatus.NEEDS_REVIEW


class TestCatalystGateAggregation:
    def test_one_pass_passes(self):
        gate = CatalystGate()
        result = gate.evaluate(_make_target(), EarningsGrowthProvider(0.30))
        assert result.passed is True

    def test_all_needs_review_fails(self):
        gate = CatalystGate()
        result = gate.evaluate(_make_target(), StubProvider())
        assert result.passed is False

    def test_has_five_checks(self):
        gate = CatalystGate()
        result = gate.evaluate(_make_target(), StubProvider())
        assert len(result.checks) == 5
        check_ids = {c.check_id for c in result.checks}
        assert check_ids == {"2A-1", "2A-2", "2A-3", "2B-2", "2D-2"}
