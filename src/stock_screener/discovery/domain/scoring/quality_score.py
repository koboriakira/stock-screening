from __future__ import annotations

from stock_screener.market_data.domain.financial_snapshot import FinancialSnapshot


def _linear_interpolate(value: float, low: float, high: float, score_low: float, score_high: float) -> float:
    if value <= low:
        return score_low
    if value >= high:
        return score_high
    return score_low + (score_high - score_low) * (value - low) / (high - low)


class QualityScorer:
    """質スコア (0-100点)
    ROE 0-35, 営業利益率 0-35, 自己資本比率 0-30
    """

    @staticmethod
    def score(snap: FinancialSnapshot) -> float:
        roe = QualityScorer.score_roe(snap.roe)
        op_margin = QualityScorer.score_operating_margin(snap.operating_margin)
        equity = QualityScorer.score_equity_ratio(snap.equity_ratio)
        return roe + op_margin + equity

    @staticmethod
    def score_roe(roe: float | None) -> float:
        """ROE: 8%以上=35, 5%=20, 0%以下=0"""
        if roe is None:
            return 0
        return _linear_interpolate(roe, 0.0, 0.08, 0.0, 35.0)

    @staticmethod
    def score_operating_margin(margin: float | None) -> float:
        """営業利益率: 10%以上=35, 5%=20, 0%以下=0"""
        if margin is None:
            return 0
        return _linear_interpolate(margin, 0.0, 0.10, 0.0, 35.0)

    @staticmethod
    def score_equity_ratio(ratio: float | None) -> float:
        """自己資本比率: 50%以上=30, 30%=15, 20%=5"""
        if ratio is None:
            return 0
        if ratio >= 0.50:
            return 30
        if ratio >= 0.30:
            return _linear_interpolate(ratio, 0.30, 0.50, 15.0, 30.0)
        if ratio >= 0.20:
            return _linear_interpolate(ratio, 0.20, 0.30, 5.0, 15.0)
        return 0
