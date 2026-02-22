from __future__ import annotations

from stock_screener.evaluation.domain.check import CheckResult, CheckStatus, GateResult
from stock_screener.evaluation.domain.data_provider import EvaluationDataProvider
from stock_screener.evaluation.domain.evaluation_target import EvaluationTarget

MARGIN_RATIO_MAX = 5.0
GOING_CONCERN_EQUITY_RATIO_FAIL = 0.10
GOING_CONCERN_EQUITY_RATIO_WARN = 0.20


class FatalFlawGate:
    """Gate1: 致命的欠陥チェック。不正会計、GC注記、信用倍率を検証する。"""

    def evaluate(self, target: EvaluationTarget, provider: EvaluationDataProvider) -> GateResult:
        """対象銘柄の致命的欠陥をチェックし、GateResult を返す。"""
        checks = [
            self._check_accounting_fraud(target, provider),
            self._check_going_concern(target, provider),
            self._check_customer_concentration(target, provider),
            self._check_ceo_change(target, provider),
            self._check_margin_trading_ratio(target, provider),
        ]
        return GateResult.for_gate1("Gate1: 致命的欠陥", checks)

    def _check_accounting_fraud(
        self, target: EvaluationTarget, provider: EvaluationDataProvider,
    ) -> CheckResult:
        status = provider.check_accounting_fraud(target.ticker)
        return CheckResult(
            check_id="1-1",
            status=status,
            description="過去3年以内に不正会計・行政処分がないか",
        )

    def _check_going_concern(
        self, target: EvaluationTarget, provider: EvaluationDataProvider,
    ) -> CheckResult:
        snap = target.financial_snapshot
        if snap.equity_ratio is None:
            return CheckResult(
                check_id="1-2",
                status=CheckStatus.NEEDS_REVIEW,
                description="継続企業の前提に関する注記がないか",
                detail="自己資本比率データなし",
            )
        if snap.equity_ratio < GOING_CONCERN_EQUITY_RATIO_FAIL:
            return CheckResult(
                check_id="1-2",
                status=CheckStatus.FAIL,
                description="継続企業の前提に関する注記がないか",
                detail=f"自己資本比率={snap.equity_ratio:.1%} 財務危機の可能性",
            )
        if snap.equity_ratio < GOING_CONCERN_EQUITY_RATIO_WARN:
            return CheckResult(
                check_id="1-2",
                status=CheckStatus.NEEDS_REVIEW,
                description="継続企業の前提に関する注記がないか",
                detail=f"自己資本比率={snap.equity_ratio:.1%} 要注意水準",
            )
        return CheckResult(
            check_id="1-2",
            status=CheckStatus.PASS,
            description="継続企業の前提に関する注記がないか",
            detail=f"自己資本比率={snap.equity_ratio:.1%}",
        )

    def _check_customer_concentration(
        self, target: EvaluationTarget, provider: EvaluationDataProvider,
    ) -> CheckResult:
        return CheckResult(
            check_id="1-3",
            status=CheckStatus.NEEDS_REVIEW,
            description="売上上位顧客への集中度が高くないか",
            detail="EDINET未接続のため手動確認が必要",
        )

    def _check_ceo_change(
        self, target: EvaluationTarget, provider: EvaluationDataProvider,
    ) -> CheckResult:
        return CheckResult(
            check_id="1-4",
            status=CheckStatus.NEEDS_REVIEW,
            description="直近1年以内に代表取締役の交代がないか",
            detail="EDINET未接続のため手動確認が必要",
        )

    def _check_margin_trading_ratio(
        self, target: EvaluationTarget, provider: EvaluationDataProvider,
    ) -> CheckResult:
        ratio = provider.get_margin_trading_ratio(target.ticker)
        if ratio is None:
            return CheckResult(
                check_id="1-5",
                status=CheckStatus.NEEDS_REVIEW,
                description="信用倍率チェック",
                detail="データ取得不可",
            )
        if ratio >= MARGIN_RATIO_MAX:
            return CheckResult(
                check_id="1-5",
                status=CheckStatus.FAIL,
                description="信用倍率チェック",
                detail=f"信用倍率: {ratio}",
            )
        return CheckResult(
            check_id="1-5",
            status=CheckStatus.PASS,
            description="信用倍率チェック",
            detail=f"信用倍率: {ratio}",
        )
