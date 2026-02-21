from __future__ import annotations

from stock_screener.market_data.domain.financial_snapshot import FinancialSnapshot


def _linear_interpolate(value: float, low: float, high: float, score_low: float, score_high: float) -> float:
    if value <= low:
        return score_low
    if value >= high:
        return score_high
    return score_low + (score_high - score_low) * (value - low) / (high - low)


class MomentumScorer:
    """変化スコア (0-100点)
    売上高成長率 0-35, 営業利益成長率 0-35, 配当利回り変化 0-30

    配当利回り変化は Phase 1 ではデータ取得が難しいため、
    現在の配当利回りをプロキシとして使用する。
    """

    @staticmethod
    def score(snap: FinancialSnapshot) -> float:
        rev = MomentumScorer.score_revenue_growth(snap.revenue_growth)
        op = MomentumScorer.score_operating_profit_growth(snap.operating_profit_growth)
        div = MomentumScorer.score_dividend_yield(snap.dividend_yield)
        return rev + op + div

    @staticmethod
    def score_revenue_growth(growth: float | None) -> float:
        """売上高成長率: 20%以上=35, 10%=20, 0%=10, マイナス=0"""
        if growth is None:
            return 0
        if growth < 0:
            return 0
        return _linear_interpolate(growth, 0.0, 0.20, 10.0, 35.0)

    @staticmethod
    def score_operating_profit_growth(growth: float | None) -> float:
        """営業利益成長率: 30%以上=35, 10%=20, 0%=5"""
        if growth is None:
            return 0
        if growth < 0:
            return 0
        return _linear_interpolate(growth, 0.0, 0.30, 5.0, 35.0)

    @staticmethod
    def score_dividend_yield(dividend_yield: float | None) -> float:
        """配当利回り(変化のプロキシ): 4%以上=30, 2%=15, 0%=0"""
        if dividend_yield is None:
            return 0
        return _linear_interpolate(dividend_yield, 0.0, 0.04, 0.0, 30.0)
