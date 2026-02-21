from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from stock_screener.evaluation.domain.check import GateResult
from stock_screener.evaluation.domain.evaluation_target import EvaluationTarget


class Verdict(Enum):
    """3-Gate 評価の最終判定。"""

    INVEST = "invest"
    REJECT = "reject"
    WATCHLIST = "watchlist"


def determine_verdict(gate1: GateResult, gate2: GateResult, gate3: GateResult) -> Verdict:  # noqa: ARG001
    """Gate1-3 の結果から最終判定を決定する。"""
    if not gate1.passed:
        return Verdict.REJECT
    if not gate2.passed:
        return Verdict.WATCHLIST
    return Verdict.INVEST


@dataclass(frozen=True)
class EvaluationReport:
    """銘柄の 3-Gate 評価レポート。Gate1-3 の結果と最終判定を保持する。"""

    target: EvaluationTarget
    gate1: GateResult
    gate2: GateResult
    gate3: GateResult
    verdict: Verdict
    evaluated_at: datetime
