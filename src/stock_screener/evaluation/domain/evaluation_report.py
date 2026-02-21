from __future__ import annotations

from enum import Enum

from stock_screener.evaluation.domain.check import GateResult


class Verdict(Enum):
    INVEST = "invest"
    REJECT = "reject"
    WATCHLIST = "watchlist"


def determine_verdict(gate1: GateResult, gate2: GateResult, gate3: GateResult) -> Verdict:  # noqa: ARG001
    if not gate1.passed:
        return Verdict.REJECT
    if not gate2.passed:
        return Verdict.WATCHLIST
    return Verdict.INVEST
