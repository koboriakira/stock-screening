from __future__ import annotations

import logging
from datetime import UTC, datetime

from stock_screener.evaluation.domain.check import GateResult
from stock_screener.evaluation.domain.data_provider import EvaluationDataProvider
from stock_screener.evaluation.domain.evaluation_report import EvaluationReport, determine_verdict
from stock_screener.evaluation.domain.evaluation_target import EvaluationTarget
from stock_screener.evaluation.domain.gate1_fatal_flaw import FatalFlawGate
from stock_screener.evaluation.domain.gate2_catalyst import CatalystGate
from stock_screener.evaluation.domain.gate3_valuation import ValuationSanityGate

logger = logging.getLogger(__name__)


class EvaluationService:
    def __init__(self, provider: EvaluationDataProvider) -> None:
        self._provider = provider
        self._gate1 = FatalFlawGate()
        self._gate2 = CatalystGate()
        self._gate3 = ValuationSanityGate()

    def execute(self, targets: list[EvaluationTarget]) -> list[EvaluationReport]:
        logger.info("評価対象: %d銘柄", len(targets))
        reports = []
        for target in targets:
            report = self._evaluate_single(target)
            reports.append(report)
            logger.info(
                "%s (%s): %s",
                target.ticker.symbol,
                target.company_name,
                report.verdict.value,
            )
        return reports

    def _evaluate_single(self, target: EvaluationTarget) -> EvaluationReport:
        gate1_result = self._gate1.evaluate(target, self._provider)

        if not gate1_result.passed:
            empty_gate2 = GateResult.for_gate2("Gate2: カタリスト", [])
            empty_gate3 = GateResult.for_gate3("Gate3: バリュエーション", [])
            verdict = determine_verdict(gate1_result, empty_gate2, empty_gate3)
            return EvaluationReport(
                target=target,
                gate1=gate1_result,
                gate2=empty_gate2,
                gate3=empty_gate3,
                verdict=verdict,
                evaluated_at=datetime.now(tz=UTC),
            )

        gate2_result = self._gate2.evaluate(target, self._provider)
        gate3_result = self._gate3.evaluate(target, self._provider)
        verdict = determine_verdict(gate1_result, gate2_result, gate3_result)

        return EvaluationReport(
            target=target,
            gate1=gate1_result,
            gate2=gate2_result,
            gate3=gate3_result,
            verdict=verdict,
            evaluated_at=datetime.now(tz=UTC),
        )
