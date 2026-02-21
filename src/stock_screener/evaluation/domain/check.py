from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CheckStatus(Enum):
    PASS = "pass"
    FAIL = "fail"
    NEEDS_REVIEW = "needs_review"


@dataclass(frozen=True)
class CheckResult:
    check_id: str
    status: CheckStatus
    description: str
    detail: str | None = None


@dataclass(frozen=True)
class GateResult:
    gate_name: str
    checks: list[CheckResult]
    passed: bool

    @classmethod
    def for_gate1(cls, gate_name: str, checks: list[CheckResult]) -> GateResult:
        passed = all(c.status != CheckStatus.FAIL for c in checks)
        return cls(gate_name=gate_name, checks=checks, passed=passed)

    @classmethod
    def for_gate2(cls, gate_name: str, checks: list[CheckResult]) -> GateResult:
        passed = any(c.status == CheckStatus.PASS for c in checks)
        return cls(gate_name=gate_name, checks=checks, passed=passed)

    @classmethod
    def for_gate3(cls, gate_name: str, checks: list[CheckResult]) -> GateResult:
        return cls(gate_name=gate_name, checks=checks, passed=True)
