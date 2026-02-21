from __future__ import annotations

from stock_screener.evaluation.domain.check import CheckStatus
from stock_screener.shared.types import Ticker


class StubEvaluationDataProvider:
    """全チェックで NEEDS_REVIEW / None を返すスタブ実装。

    Phase 2 では外部データソース(EDINET, TDnet等)が未接続のため、
    データ取得不可のチェック項目はこのスタブを経由して NEEDS_REVIEW を返す。
    Phase 3 で実データソースに差し替え可能。
    """

    def check_accounting_fraud(self, ticker: Ticker) -> CheckStatus:
        return CheckStatus.NEEDS_REVIEW

    def check_going_concern(self, ticker: Ticker) -> CheckStatus:
        return CheckStatus.NEEDS_REVIEW

    def get_margin_trading_ratio(self, ticker: Ticker) -> float | None:
        return None

    def get_earnings_growth_forecast(self, ticker: Ticker) -> float | None:
        return None

    def get_quarterly_progress_improvement(self, ticker: Ticker) -> float | None:
        return None

    def has_upward_revision(self, ticker: Ticker) -> bool | None:
        return None

    def has_share_buyback(self, ticker: Ticker) -> bool | None:
        return None

    def get_per_percentile_in_5y_range(self, ticker: Ticker) -> float | None:
        return None
