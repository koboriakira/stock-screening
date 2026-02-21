from __future__ import annotations

from stock_screener.evaluation.domain.check import CheckStatus
from stock_screener.evaluation.domain.evaluation_target import EvaluationTarget
from stock_screener.evaluation.domain.gate3_valuation import ValuationSanityGate
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


class PerPercentileProvider(StubProvider):
    def __init__(self, percentile: float | None):
        self._percentile = percentile

    def get_per_percentile_in_5y_range(self, ticker: Ticker) -> float | None:
        return self._percentile


class TestCheckNetCash:
    def test_above_30_passes(self):
        gate = ValuationSanityGate()
        target = _make_target(financial_snapshot=FinancialSnapshot(net_cash_ratio=0.35))
        result = gate.evaluate(target, StubProvider())
        check = next(c for c in result.checks if c.check_id == "3-3")
        assert check.status == CheckStatus.PASS

    def test_below_30_fails(self):
        gate = ValuationSanityGate()
        target = _make_target(financial_snapshot=FinancialSnapshot(net_cash_ratio=0.20))
        result = gate.evaluate(target, StubProvider())
        check = next(c for c in result.checks if c.check_id == "3-3")
        assert check.status == CheckStatus.FAIL

    def test_exactly_30_passes(self):
        gate = ValuationSanityGate()
        target = _make_target(financial_snapshot=FinancialSnapshot(net_cash_ratio=0.30))
        result = gate.evaluate(target, StubProvider())
        check = next(c for c in result.checks if c.check_id == "3-3")
        assert check.status == CheckStatus.PASS

    def test_none_needs_review(self):
        gate = ValuationSanityGate()
        target = _make_target(financial_snapshot=FinancialSnapshot())
        result = gate.evaluate(target, StubProvider())
        check = next(c for c in result.checks if c.check_id == "3-3")
        assert check.status == CheckStatus.NEEDS_REVIEW


class TestCheckPerRange:
    def test_in_lower_25_passes(self):
        gate = ValuationSanityGate()
        result = gate.evaluate(_make_target(), PerPercentileProvider(20.0))
        check = next(c for c in result.checks if c.check_id == "3-2")
        assert check.status == CheckStatus.PASS

    def test_above_lower_25_fails(self):
        gate = ValuationSanityGate()
        result = gate.evaluate(_make_target(), PerPercentileProvider(50.0))
        check = next(c for c in result.checks if c.check_id == "3-2")
        assert check.status == CheckStatus.FAIL

    def test_none_needs_review(self):
        gate = ValuationSanityGate()
        result = gate.evaluate(_make_target(), StubProvider())
        check = next(c for c in result.checks if c.check_id == "3-2")
        assert check.status == CheckStatus.NEEDS_REVIEW


class TestValuationSanityGateAggregation:
    def test_always_passes(self):
        gate = ValuationSanityGate()
        target = _make_target(financial_snapshot=FinancialSnapshot(net_cash_ratio=0.10))
        result = gate.evaluate(target, PerPercentileProvider(50.0))
        assert result.passed is True

    def test_has_two_checks(self):
        gate = ValuationSanityGate()
        result = gate.evaluate(_make_target(), StubProvider())
        assert len(result.checks) == 2
        check_ids = {c.check_id for c in result.checks}
        assert check_ids == {"3-2", "3-3"}
