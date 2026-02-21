from __future__ import annotations

from stock_screener.evaluation.domain.check import CheckResult, CheckStatus, GateResult
from stock_screener.evaluation.domain.evaluation_report import Verdict, determine_verdict


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
