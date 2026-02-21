from __future__ import annotations

import pytest

from stock_screener.evaluation.domain.check import CheckResult, CheckStatus, GateResult


class TestCheckStatus:
    def test_values(self):
        assert CheckStatus.PASS.value == "pass"
        assert CheckStatus.FAIL.value == "fail"
        assert CheckStatus.NEEDS_REVIEW.value == "needs_review"


class TestCheckResult:
    def test_creation(self):
        result = CheckResult(
            check_id="1-1",
            status=CheckStatus.PASS,
            description="不正会計チェック",
        )
        assert result.check_id == "1-1"
        assert result.status == CheckStatus.PASS
        assert result.description == "不正会計チェック"
        assert result.detail is None

    def test_creation_with_detail(self):
        result = CheckResult(
            check_id="1-5",
            status=CheckStatus.FAIL,
            description="信用倍率チェック",
            detail="信用倍率: 6.2",
        )
        assert result.detail == "信用倍率: 6.2"

    def test_is_frozen(self):
        result = CheckResult(check_id="1-1", status=CheckStatus.PASS, description="test")
        with pytest.raises(AttributeError):
            result.status = CheckStatus.FAIL  # type: ignore[misc]


class TestGateResult:
    def test_gate1_all_pass(self):
        checks = [
            CheckResult("1-1", CheckStatus.PASS, "チェック1"),
            CheckResult("1-2", CheckStatus.PASS, "チェック2"),
        ]
        gate = GateResult.for_gate1("Gate1", checks)
        assert gate.passed is True

    def test_gate1_has_fail(self):
        checks = [
            CheckResult("1-1", CheckStatus.PASS, "チェック1"),
            CheckResult("1-2", CheckStatus.FAIL, "チェック2"),
        ]
        gate = GateResult.for_gate1("Gate1", checks)
        assert gate.passed is False

    def test_gate1_needs_review_still_passes(self):
        checks = [
            CheckResult("1-1", CheckStatus.NEEDS_REVIEW, "チェック1"),
            CheckResult("1-2", CheckStatus.NEEDS_REVIEW, "チェック2"),
        ]
        gate = GateResult.for_gate1("Gate1", checks)
        assert gate.passed is True

    def test_gate2_one_pass(self):
        checks = [
            CheckResult("2A-1", CheckStatus.NEEDS_REVIEW, "チェック1"),
            CheckResult("2A-2", CheckStatus.PASS, "チェック2"),
        ]
        gate = GateResult.for_gate2("Gate2", checks)
        assert gate.passed is True

    def test_gate2_no_pass(self):
        checks = [
            CheckResult("2A-1", CheckStatus.NEEDS_REVIEW, "チェック1"),
            CheckResult("2A-2", CheckStatus.FAIL, "チェック2"),
        ]
        gate = GateResult.for_gate2("Gate2", checks)
        assert gate.passed is False

    def test_gate3_always_passes(self):
        checks = [
            CheckResult("3-2", CheckStatus.FAIL, "チェック1"),
            CheckResult("3-3", CheckStatus.FAIL, "チェック2"),
        ]
        gate = GateResult.for_gate3("Gate3", checks)
        assert gate.passed is True

    def test_gate_result_has_name_and_checks(self):
        checks = [CheckResult("1-1", CheckStatus.PASS, "テスト")]
        gate = GateResult.for_gate1("Gate1: 致命的欠陥", checks)
        assert gate.gate_name == "Gate1: 致命的欠陥"
        assert len(gate.checks) == 1
