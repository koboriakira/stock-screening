from __future__ import annotations

from datetime import UTC, datetime

import pytest

from stock_screener.evaluation.domain.check import CheckResult, CheckStatus, GateResult
from stock_screener.evaluation.domain.evaluation_report import EvaluationReport, Verdict, determine_verdict
from stock_screener.evaluation.domain.evaluation_target import EvaluationTarget
from stock_screener.market_data.domain.financial_snapshot import FinancialSnapshot
from stock_screener.shared.types import Ticker


def _gate1(checks: list[CheckResult]) -> GateResult:
    return GateResult.for_gate1("Gate1", checks)


def _gate2(checks: list[CheckResult]) -> GateResult:
    return GateResult.for_gate2("Gate2", checks)


def _gate3(checks: list[CheckResult]) -> GateResult:
    return GateResult.for_gate3("Gate3", checks)


def _pass_check(check_id: str = "x") -> CheckResult:
    return CheckResult(check_id, CheckStatus.PASS, "テスト")


def _fail_check(check_id: str = "x") -> CheckResult:
    return CheckResult(check_id, CheckStatus.FAIL, "テスト")


def _review_check(check_id: str = "x") -> CheckResult:
    return CheckResult(check_id, CheckStatus.NEEDS_REVIEW, "テスト")


class TestVerdict:
    def test_values(self):
        assert Verdict.INVEST.value == "invest"
        assert Verdict.REJECT.value == "reject"
        assert Verdict.WATCHLIST.value == "watchlist"


class TestDetermineVerdict:
    def test_invest(self):
        g1 = _gate1([_pass_check()])
        g2 = _gate2([_pass_check()])
        g3 = _gate3([_pass_check()])
        assert determine_verdict(g1, g2, g3) == Verdict.INVEST

    def test_reject_gate1_fail(self):
        g1 = _gate1([_fail_check()])
        g2 = _gate2([_pass_check()])
        g3 = _gate3([_pass_check()])
        assert determine_verdict(g1, g2, g3) == Verdict.REJECT

    def test_watchlist_no_catalyst(self):
        g1 = _gate1([_pass_check()])
        g2 = _gate2([_fail_check()])
        g3 = _gate3([_pass_check()])
        assert determine_verdict(g1, g2, g3) == Verdict.WATCHLIST

    def test_watchlist_gate2_all_needs_review(self):
        g1 = _gate1([_pass_check()])
        g2 = _gate2([_review_check()])
        g3 = _gate3([_pass_check()])
        assert determine_verdict(g1, g2, g3) == Verdict.WATCHLIST

    def test_invest_gate1_needs_review_gate2_pass(self):
        g1 = _gate1([_review_check()])
        g2 = _gate2([_pass_check()])
        g3 = _gate3([_review_check()])
        assert determine_verdict(g1, g2, g3) == Verdict.INVEST


class TestEvaluationReport:
    def test_creation(self):
        target = EvaluationTarget(
            ticker=Ticker("7203"),
            company_name="トヨタ自動車",
            sector="輸送用機器",
            financial_snapshot=FinancialSnapshot(per=10.0),
            discovery_rank=1,
            score_total=80.0,
        )
        g1 = _gate1([_pass_check("1-1")])
        g2 = _gate2([_pass_check("2A-2")])
        g3 = _gate3([_pass_check("3-3")])
        now = datetime.now(tz=UTC)
        report = EvaluationReport(
            target=target,
            gate1=g1,
            gate2=g2,
            gate3=g3,
            verdict=Verdict.INVEST,
            evaluated_at=now,
        )
        assert report.target.ticker == Ticker("7203")
        assert report.verdict == Verdict.INVEST
        assert report.gate1.passed is True

    def test_is_frozen(self):
        target = EvaluationTarget(
            ticker=Ticker("7203"),
            company_name="テスト",
            sector="テスト",
            financial_snapshot=FinancialSnapshot(),
            discovery_rank=1,
            score_total=0.0,
        )
        report = EvaluationReport(
            target=target,
            gate1=_gate1([]),
            gate2=_gate2([]),
            gate3=_gate3([]),
            verdict=Verdict.REJECT,
            evaluated_at=datetime.now(tz=UTC),
        )
        with pytest.raises(AttributeError):
            report.verdict = Verdict.INVEST  # type: ignore[misc]
