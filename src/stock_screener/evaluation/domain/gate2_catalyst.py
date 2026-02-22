from __future__ import annotations

from stock_screener.evaluation.domain.check import CheckResult, CheckStatus, GateResult
from stock_screener.evaluation.domain.data_provider import EvaluationDataProvider
from stock_screener.evaluation.domain.evaluation_target import EvaluationTarget

EARNINGS_GROWTH_MIN = 0.20
EARNINGS_GROWTH_MAX = 5.0
EARNINGS_GROWTH_MIN_LIMIT = -0.95
TOB_PBR_MAX = 1.0
TOB_NET_CASH_MIN = 0.30
DIVIDEND_YIELD_THRESHOLD = 0.03


class CatalystGate:
    """Gate2: カタリストチェック。株価上昇の触媒となる材料の有無を検証する。"""

    def evaluate(self, target: EvaluationTarget, provider: EvaluationDataProvider) -> GateResult:
        """対象銘柄のカタリストをチェックし、1つ以上 PASS で通過。"""
        checks = [
            self._check_2a1_quarterly_progress(target, provider),
            self._check_2a2_earnings_growth(target, provider),
            self._check_2a3_upward_revision(target, provider),
            self._check_2b1_pbr_improvement(target, provider),
            self._check_2b2_share_buyback(target, provider),
            self._check_2b3_dividend_policy(target, provider),
            self._check_2c1_unprofitable_exit(target, provider),
            self._check_2c2_new_business(target, provider),
            self._check_2d1_major_shareholder_sale(target, provider),
            self._check_2d2_tob_mbo(target, provider),
        ]
        return GateResult.for_gate2("Gate2: カタリスト", checks)

    def _check_2a1_quarterly_progress(
        self, target: EvaluationTarget, provider: EvaluationDataProvider,
    ) -> CheckResult:
        improvement = provider.get_quarterly_progress_improvement(target.ticker)
        if improvement is None:
            return CheckResult("2A-1", CheckStatus.NEEDS_REVIEW, "四半期進捗率改善", "データ取得不可")
        if improvement >= 0.05:
            return CheckResult("2A-1", CheckStatus.PASS, "四半期進捗率改善", f"改善幅: {improvement:.1%}")
        return CheckResult("2A-1", CheckStatus.FAIL, "四半期進捗率改善", f"改善幅: {improvement:.1%}")

    def _check_2a2_earnings_growth(
        self, target: EvaluationTarget, provider: EvaluationDataProvider,
    ) -> CheckResult:
        growth = provider.get_earnings_growth_forecast(target.ticker)
        if growth is None:
            return CheckResult("2A-2", CheckStatus.NEEDS_REVIEW, "営業利益予想成長率", "データ取得不可")
        if growth > EARNINGS_GROWTH_MAX or growth < EARNINGS_GROWTH_MIN_LIMIT:
            return CheckResult(
                "2A-2", CheckStatus.NEEDS_REVIEW, "営業利益予想成長率",
                f"成長率 {growth:.1%} は異常値の可能性(範囲: -95%〜+500%)。データを手動確認してください。",
            )
        if growth >= EARNINGS_GROWTH_MIN:
            return CheckResult("2A-2", CheckStatus.PASS, "営業利益予想成長率", f"成長率: {growth:.1%}")
        return CheckResult("2A-2", CheckStatus.FAIL, "営業利益予想成長率", f"成長率: {growth:.1%}")

    def _check_2a3_upward_revision(
        self, target: EvaluationTarget, provider: EvaluationDataProvider,
    ) -> CheckResult:
        has_revision = provider.has_upward_revision(target.ticker)
        if has_revision is None:
            return CheckResult("2A-3", CheckStatus.NEEDS_REVIEW, "上方修正実績", "データ取得不可")
        if has_revision:
            return CheckResult("2A-3", CheckStatus.PASS, "上方修正実績", "直近1年以内に上方修正あり")
        return CheckResult("2A-3", CheckStatus.FAIL, "上方修正実績", "上方修正なし")

    def _check_2b1_pbr_improvement(
        self, target: EvaluationTarget, provider: EvaluationDataProvider,
    ) -> CheckResult:
        snap = target.financial_snapshot
        if snap.pbr is None:
            return CheckResult("2B-1", CheckStatus.NEEDS_REVIEW, "PBR1倍割れ改善要請", "データ不足")
        if snap.pbr < 1.0:
            return CheckResult(
                "2B-1", CheckStatus.NEEDS_REVIEW, "PBR1倍割れ改善要請",
                f"PBR={snap.pbr:.2f} 東証改善要請対象の可能性あり（手動確認）",
            )
        return CheckResult(
            "2B-1", CheckStatus.FAIL, "PBR1倍割れ改善要請",
            f"PBR={snap.pbr:.2f} 改善要請対象外",
        )

    def _check_2b2_share_buyback(
        self, target: EvaluationTarget, provider: EvaluationDataProvider,
    ) -> CheckResult:
        has_buyback = provider.has_share_buyback(target.ticker)
        if has_buyback is None:
            return CheckResult("2B-2", CheckStatus.NEEDS_REVIEW, "自社株買い", "データ取得不可")
        if has_buyback:
            return CheckResult("2B-2", CheckStatus.PASS, "自社株買い", "自社株買い実施/発表あり")
        return CheckResult("2B-2", CheckStatus.FAIL, "自社株買い", "自社株買いなし")

    def _check_2b3_dividend_policy(
        self, target: EvaluationTarget, provider: EvaluationDataProvider,
    ) -> CheckResult:
        snap = target.financial_snapshot
        if snap.dividend_yield is None:
            return CheckResult("2B-3", CheckStatus.NEEDS_REVIEW, "配当性向引き上げ", "データ不足")
        if snap.dividend_yield >= DIVIDEND_YIELD_THRESHOLD:
            return CheckResult(
                "2B-3", CheckStatus.NEEDS_REVIEW, "配当性向引き上げ",
                f"配当利回り={snap.dividend_yield:.1%} 配当方針変更の確認が必要",
            )
        return CheckResult(
            "2B-3", CheckStatus.FAIL, "配当性向引き上げ",
            f"配当利回り={snap.dividend_yield:.1%} 低水準",
        )

    def _check_2c1_unprofitable_exit(
        self, target: EvaluationTarget, provider: EvaluationDataProvider,
    ) -> CheckResult:
        return CheckResult(
            "2C-1", CheckStatus.NEEDS_REVIEW, "不採算事業撤退",
            "データソース未接続のため手動確認が必要",
        )

    def _check_2c2_new_business(
        self, target: EvaluationTarget, provider: EvaluationDataProvider,
    ) -> CheckResult:
        return CheckResult(
            "2C-2", CheckStatus.NEEDS_REVIEW, "新規事業・事業転換",
            "データソース未接続のため手動確認が必要",
        )

    def _check_2d1_major_shareholder_sale(
        self, target: EvaluationTarget, provider: EvaluationDataProvider,
    ) -> CheckResult:
        return CheckResult(
            "2D-1", CheckStatus.NEEDS_REVIEW, "大株主による売却",
            "データソース未接続のため手動確認が必要",
        )

    def _check_2d2_tob_mbo(
        self, target: EvaluationTarget, provider: EvaluationDataProvider,
    ) -> CheckResult:
        snap = target.financial_snapshot
        if snap.pbr is None or snap.net_cash_ratio is None:
            return CheckResult("2D-2", CheckStatus.NEEDS_REVIEW, "TOB/MBO構造", "データ不足")
        if snap.pbr < TOB_PBR_MAX and snap.net_cash_ratio >= TOB_NET_CASH_MIN:
            return CheckResult(
                "2D-2", CheckStatus.PASS, "TOB/MBO構造",
                f"PBR={snap.pbr:.2f}, ネットキャッシュ比率={snap.net_cash_ratio:.1%}",
            )
        return CheckResult(
            "2D-2", CheckStatus.FAIL, "TOB/MBO構造",
            f"PBR={snap.pbr:.2f}, ネットキャッシュ比率={snap.net_cash_ratio:.1%}",
        )
