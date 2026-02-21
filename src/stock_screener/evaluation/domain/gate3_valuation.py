from __future__ import annotations

from stock_screener.evaluation.domain.check import CheckResult, CheckStatus, GateResult
from stock_screener.evaluation.domain.data_provider import EvaluationDataProvider
from stock_screener.evaluation.domain.evaluation_target import EvaluationTarget

NET_CASH_RATIO_MIN = 0.30
PER_PERCENTILE_MAX = 25.0


class ValuationSanityGate:
    """Gate3: バリュエーション健全性チェック。PER水準とネットキャッシュ比率を検証する。"""

    def evaluate(self, target: EvaluationTarget, provider: EvaluationDataProvider) -> GateResult:
        """対象銘柄のバリュエーション指標をチェックする(常に通過)。"""
        checks = [
            self._check_3_2_per_range(target, provider),
            self._check_3_3_net_cash(target, provider),
        ]
        return GateResult.for_gate3("Gate3: バリュエーション", checks)

    def _check_3_2_per_range(
        self, target: EvaluationTarget, provider: EvaluationDataProvider,
    ) -> CheckResult:
        percentile = provider.get_per_percentile_in_5y_range(target.ticker)
        if percentile is None:
            return CheckResult("3-2", CheckStatus.NEEDS_REVIEW, "PER 5年レンジ下位25%", "データ取得不可")
        if percentile <= PER_PERCENTILE_MAX:
            return CheckResult("3-2", CheckStatus.PASS, "PER 5年レンジ下位25%", f"パーセンタイル: {percentile:.0f}%")
        return CheckResult("3-2", CheckStatus.FAIL, "PER 5年レンジ下位25%", f"パーセンタイル: {percentile:.0f}%")

    def _check_3_3_net_cash(
        self, target: EvaluationTarget, provider: EvaluationDataProvider,
    ) -> CheckResult:
        ratio = target.financial_snapshot.net_cash_ratio
        if ratio is None:
            return CheckResult("3-3", CheckStatus.NEEDS_REVIEW, "ネットキャッシュ比率", "データなし")
        if ratio >= NET_CASH_RATIO_MIN:
            return CheckResult("3-3", CheckStatus.PASS, "ネットキャッシュ比率", f"比率: {ratio:.1%}")
        return CheckResult("3-3", CheckStatus.FAIL, "ネットキャッシュ比率", f"比率: {ratio:.1%}")
