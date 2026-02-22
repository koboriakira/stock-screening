from __future__ import annotations

from stock_screener.evaluation.domain.check import CheckStatus
from stock_screener.evaluation.domain.evaluation_target import EvaluationTarget
from stock_screener.evaluation.domain.gate1_fatal_flaw import FatalFlawGate
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
    """全チェックで NEEDS_REVIEW を返すスタブ"""

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


class FraudDetectedProvider(StubProvider):
    def check_accounting_fraud(self, ticker: Ticker) -> CheckStatus:
        return CheckStatus.FAIL


class GoingConcernProvider(StubProvider):
    def check_going_concern(self, ticker: Ticker) -> CheckStatus:
        return CheckStatus.FAIL


class HighMarginRatioProvider(StubProvider):
    def __init__(self, ratio: float):
        self._ratio = ratio

    def get_margin_trading_ratio(self, ticker: Ticker) -> float | None:
        return self._ratio


class TestFatalFlawGate:
    def test_all_needs_review_passes(self):
        gate = FatalFlawGate()
        result = gate.evaluate(_make_target(), StubProvider())
        assert result.passed is True
        assert all(c.status == CheckStatus.NEEDS_REVIEW for c in result.checks)

    def test_fraud_detected_fails(self):
        gate = FatalFlawGate()
        result = gate.evaluate(_make_target(), FraudDetectedProvider())
        assert result.passed is False
        fraud_check = next(c for c in result.checks if c.check_id == "1-1")
        assert fraud_check.status == CheckStatus.FAIL

    def test_going_concern_fails(self):
        gate = FatalFlawGate()
        target = _make_target(financial_snapshot=FinancialSnapshot(equity_ratio=0.05))
        result = gate.evaluate(target, StubProvider())
        assert result.passed is False
        gc_check = next(c for c in result.checks if c.check_id == "1-2")
        assert gc_check.status == CheckStatus.FAIL

    def test_high_margin_ratio_fails(self):
        gate = FatalFlawGate()
        result = gate.evaluate(_make_target(), HighMarginRatioProvider(6.2))
        assert result.passed is False
        mr_check = next(c for c in result.checks if c.check_id == "1-5")
        assert mr_check.status == CheckStatus.FAIL
        assert "6.2" in (mr_check.detail or "")

    def test_margin_ratio_below_threshold_passes(self):
        gate = FatalFlawGate()
        result = gate.evaluate(_make_target(), HighMarginRatioProvider(3.0))
        assert result.passed is True
        mr_check = next(c for c in result.checks if c.check_id == "1-5")
        assert mr_check.status == CheckStatus.PASS

    def test_margin_ratio_none_needs_review(self):
        gate = FatalFlawGate()
        result = gate.evaluate(_make_target(), StubProvider())
        mr_check = next(c for c in result.checks if c.check_id == "1-5")
        assert mr_check.status == CheckStatus.NEEDS_REVIEW

    def test_has_five_checks(self):
        gate = FatalFlawGate()
        result = gate.evaluate(_make_target(), StubProvider())
        assert len(result.checks) == 5
        check_ids = {c.check_id for c in result.checks}
        assert check_ids == {"1-1", "1-2", "1-3", "1-4", "1-5"}

    def test_customer_concentration_needs_review(self):
        """1-3: 顧客集中度チェックは EDINET未接続のため NEEDS_REVIEW を返す。"""
        gate = FatalFlawGate()
        result = gate.evaluate(_make_target(), StubProvider())
        check = next(c for c in result.checks if c.check_id == "1-3")
        assert check.status == CheckStatus.NEEDS_REVIEW
        assert "集中度" in check.description

    def test_ceo_change_needs_review(self):
        """1-4: 代表取締役交代チェックは EDINET未接続のため NEEDS_REVIEW を返す。"""
        gate = FatalFlawGate()
        result = gate.evaluate(_make_target(), StubProvider())
        check = next(c for c in result.checks if c.check_id == "1-4")
        assert check.status == CheckStatus.NEEDS_REVIEW
        assert "代表取締役" in check.description

    def test_customer_concentration_and_ceo_change_do_not_fail_gate(self):
        """1-3, 1-4 が NEEDS_REVIEW でもゲートは通過する。"""
        gate = FatalFlawGate()
        result = gate.evaluate(_make_target(), StubProvider())
        assert result.passed is True


class TestCheck12GoingConcern:
    """1-2: 継続企業注記チェック — FinancialSnapshot の equity_ratio で3段階判定。"""

    def test_equity_ratio_below_10_fails(self):
        """自己資本比率 < 10% → FAIL (財務危機)。"""
        gate = FatalFlawGate()
        target = _make_target(financial_snapshot=FinancialSnapshot(equity_ratio=0.08))
        result = gate.evaluate(target, StubProvider())
        check = next(c for c in result.checks if c.check_id == "1-2")
        assert check.status == CheckStatus.FAIL
        assert result.passed is False

    def test_equity_ratio_between_10_and_20_needs_review(self):
        """自己資本比率 10%-20% → NEEDS_REVIEW (要注意)。"""
        gate = FatalFlawGate()
        target = _make_target(financial_snapshot=FinancialSnapshot(equity_ratio=0.15))
        result = gate.evaluate(target, StubProvider())
        check = next(c for c in result.checks if c.check_id == "1-2")
        assert check.status == CheckStatus.NEEDS_REVIEW

    def test_equity_ratio_above_20_passes(self):
        """自己資本比率 >= 20% → PASS。"""
        gate = FatalFlawGate()
        target = _make_target(financial_snapshot=FinancialSnapshot(equity_ratio=0.35))
        result = gate.evaluate(target, StubProvider())
        check = next(c for c in result.checks if c.check_id == "1-2")
        assert check.status == CheckStatus.PASS

    def test_equity_ratio_none_needs_review(self):
        """自己資本比率データなし → NEEDS_REVIEW。"""
        gate = FatalFlawGate()
        target = _make_target(financial_snapshot=FinancialSnapshot())
        result = gate.evaluate(target, StubProvider())
        check = next(c for c in result.checks if c.check_id == "1-2")
        assert check.status == CheckStatus.NEEDS_REVIEW

    def test_equity_ratio_exactly_10_needs_review(self):
        """自己資本比率ちょうど10% → NEEDS_REVIEW (要注意、FAILではない)。"""
        gate = FatalFlawGate()
        target = _make_target(financial_snapshot=FinancialSnapshot(equity_ratio=0.10))
        result = gate.evaluate(target, StubProvider())
        check = next(c for c in result.checks if c.check_id == "1-2")
        assert check.status == CheckStatus.NEEDS_REVIEW

    def test_equity_ratio_exactly_20_passes(self):
        """自己資本比率ちょうど20% → PASS。"""
        gate = FatalFlawGate()
        target = _make_target(financial_snapshot=FinancialSnapshot(equity_ratio=0.20))
        result = gate.evaluate(target, StubProvider())
        check = next(c for c in result.checks if c.check_id == "1-2")
        assert check.status == CheckStatus.PASS
