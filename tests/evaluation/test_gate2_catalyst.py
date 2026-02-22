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


class QuarterlyProgressProvider(StubProvider):
    def __init__(self, improvement: float | None):
        self._improvement = improvement

    def get_quarterly_progress_improvement(self, ticker: Ticker) -> float | None:
        return self._improvement


class UpwardRevisionProvider(StubProvider):
    def __init__(self, has_revision: bool | None):
        self._has_revision = has_revision

    def has_upward_revision(self, ticker: Ticker) -> bool | None:
        return self._has_revision


class ShareBuybackProvider(StubProvider):
    def __init__(self, has_buyback: bool | None):
        self._has_buyback = has_buyback

    def has_share_buyback(self, ticker: Ticker) -> bool | None:
        return self._has_buyback


class TestCheck2A1QuarterlyProgress:
    def test_improvement_above_threshold_passes(self):
        gate = CatalystGate()
        result = gate.evaluate(_make_target(), QuarterlyProgressProvider(0.10))
        check = next(c for c in result.checks if c.check_id == "2A-1")
        assert check.status == CheckStatus.PASS

    def test_improvement_below_threshold_fails(self):
        gate = CatalystGate()
        result = gate.evaluate(_make_target(), QuarterlyProgressProvider(0.02))
        check = next(c for c in result.checks if c.check_id == "2A-1")
        assert check.status == CheckStatus.FAIL

    def test_exactly_threshold_passes(self):
        gate = CatalystGate()
        result = gate.evaluate(_make_target(), QuarterlyProgressProvider(0.05))
        check = next(c for c in result.checks if c.check_id == "2A-1")
        assert check.status == CheckStatus.PASS


class TestCheck2A3UpwardRevision:
    def test_has_revision_passes(self):
        gate = CatalystGate()
        result = gate.evaluate(_make_target(), UpwardRevisionProvider(True))
        check = next(c for c in result.checks if c.check_id == "2A-3")
        assert check.status == CheckStatus.PASS

    def test_no_revision_fails(self):
        gate = CatalystGate()
        result = gate.evaluate(_make_target(), UpwardRevisionProvider(False))
        check = next(c for c in result.checks if c.check_id == "2A-3")
        assert check.status == CheckStatus.FAIL


class TestCheck2B2ShareBuyback:
    def test_has_buyback_passes(self):
        gate = CatalystGate()
        result = gate.evaluate(_make_target(), ShareBuybackProvider(True))
        check = next(c for c in result.checks if c.check_id == "2B-2")
        assert check.status == CheckStatus.PASS

    def test_no_buyback_fails(self):
        gate = CatalystGate()
        result = gate.evaluate(_make_target(), ShareBuybackProvider(False))
        check = next(c for c in result.checks if c.check_id == "2B-2")
        assert check.status == CheckStatus.FAIL


class TestCatalystGateAggregation:
    def test_one_pass_passes(self):
        gate = CatalystGate()
        result = gate.evaluate(_make_target(), EarningsGrowthProvider(0.30))
        assert result.passed is True

    def test_all_needs_review_fails(self):
        gate = CatalystGate()
        result = gate.evaluate(_make_target(), StubProvider())
        assert result.passed is False

    def test_has_ten_checks(self):
        gate = CatalystGate()
        result = gate.evaluate(_make_target(), StubProvider())
        assert len(result.checks) == 10
        check_ids = {c.check_id for c in result.checks}
        assert check_ids == {
            "2A-1", "2A-2", "2A-3",
            "2B-1", "2B-2", "2B-3",
            "2C-1", "2C-2",
            "2D-1", "2D-2",
        }


class TestCheck2B1PbrImprovement:
    """2B-1: PBR1倍割れ + 改善要請チェック。"""

    def test_pbr_below_1_needs_review(self):
        """PBR < 1.0 の場合は NEEDS_REVIEW(改善要請の確認が必要)。"""
        gate = CatalystGate()
        target = _make_target(financial_snapshot=FinancialSnapshot(pbr=0.7))
        result = gate.evaluate(target, StubProvider())
        check = next(c for c in result.checks if c.check_id == "2B-1")
        assert check.status == CheckStatus.NEEDS_REVIEW
        assert "PBR" in check.description

    def test_pbr_above_1_fails(self):
        """PBR >= 1.0 の場合は FAIL(PBR改善要請の対象外)。"""
        gate = CatalystGate()
        target = _make_target(financial_snapshot=FinancialSnapshot(pbr=1.2))
        result = gate.evaluate(target, StubProvider())
        check = next(c for c in result.checks if c.check_id == "2B-1")
        assert check.status == CheckStatus.FAIL

    def test_pbr_none_needs_review(self):
        """PBR データなしの場合は NEEDS_REVIEW。"""
        gate = CatalystGate()
        target = _make_target(financial_snapshot=FinancialSnapshot())
        result = gate.evaluate(target, StubProvider())
        check = next(c for c in result.checks if c.check_id == "2B-1")
        assert check.status == CheckStatus.NEEDS_REVIEW


class TestCheck2B3DividendPolicy:
    """2B-3: 配当性向引き上げチェック。"""

    def test_dividend_yield_3pct_needs_review(self):
        """配当利回り >= 3% の場合は NEEDS_REVIEW(配当方針の確認が必要)。"""
        gate = CatalystGate()
        target = _make_target(financial_snapshot=FinancialSnapshot(dividend_yield=0.04))
        result = gate.evaluate(target, StubProvider())
        check = next(c for c in result.checks if c.check_id == "2B-3")
        assert check.status == CheckStatus.NEEDS_REVIEW
        assert "配当" in check.description

    def test_dividend_yield_below_3pct_fails(self):
        """配当利回り < 3% の場合は FAIL。"""
        gate = CatalystGate()
        target = _make_target(financial_snapshot=FinancialSnapshot(dividend_yield=0.02))
        result = gate.evaluate(target, StubProvider())
        check = next(c for c in result.checks if c.check_id == "2B-3")
        assert check.status == CheckStatus.FAIL

    def test_dividend_yield_none_needs_review(self):
        """配当利回りデータなしの場合は NEEDS_REVIEW。"""
        gate = CatalystGate()
        target = _make_target(financial_snapshot=FinancialSnapshot())
        result = gate.evaluate(target, StubProvider())
        check = next(c for c in result.checks if c.check_id == "2B-3")
        assert check.status == CheckStatus.NEEDS_REVIEW


class TestCheck2C1UnprofitableExit:
    """2C-1: 不採算事業撤退チェック(スタブ)。"""

    def test_always_needs_review(self):
        gate = CatalystGate()
        result = gate.evaluate(_make_target(), StubProvider())
        check = next(c for c in result.checks if c.check_id == "2C-1")
        assert check.status == CheckStatus.NEEDS_REVIEW
        assert "不採算" in check.description


class TestCheck2C2NewBusiness:
    """2C-2: 新規事業チェック(スタブ)。"""

    def test_always_needs_review(self):
        gate = CatalystGate()
        result = gate.evaluate(_make_target(), StubProvider())
        check = next(c for c in result.checks if c.check_id == "2C-2")
        assert check.status == CheckStatus.NEEDS_REVIEW
        assert "新規事業" in check.description


class TestCheck2D1MajorShareholderSale:
    """2D-1: 大株主売却チェック(スタブ)。"""

    def test_always_needs_review(self):
        gate = CatalystGate()
        result = gate.evaluate(_make_target(), StubProvider())
        check = next(c for c in result.checks if c.check_id == "2D-1")
        assert check.status == CheckStatus.NEEDS_REVIEW
        assert "大株主" in check.description
