from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CheckStatus(Enum):
    """個別チェック項目の判定ステータス。"""

    PASS = "pass"
    FAIL = "fail"
    NEEDS_REVIEW = "needs_review"


@dataclass(frozen=True)
class CheckResult:
    """個別チェック項目の判定結果。"""

    check_id: str
    status: CheckStatus
    description: str
    detail: str | None = None


@dataclass(frozen=True)
class GateResult:
    """ゲート単位の判定結果。複数の CheckResult を集約する。"""

    gate_name: str
    checks: list[CheckResult]
    passed: bool

    @classmethod
    def for_gate1(cls, gate_name: str, checks: list[CheckResult]) -> GateResult:
        """Gate1: 全チェックが FAIL でなければ通過。"""
        passed = all(c.status != CheckStatus.FAIL for c in checks)
        return cls(gate_name=gate_name, checks=checks, passed=passed)

    @classmethod
    def for_gate2(cls, gate_name: str, checks: list[CheckResult]) -> GateResult:
        """Gate2: 1つ以上が PASS であれば通過。"""
        passed = any(c.status == CheckStatus.PASS for c in checks)
        return cls(gate_name=gate_name, checks=checks, passed=passed)

    @classmethod
    def for_gate3(cls, gate_name: str, checks: list[CheckResult]) -> GateResult:
        """Gate3: 常に通過(情報提供のみ)。"""
        return cls(gate_name=gate_name, checks=checks, passed=True)
