from __future__ import annotations

from stock_screener.market_data.domain.financial_snapshot import FinancialSnapshot


def _linear_interpolate(value: float, low: float, high: float, score_low: float, score_high: float) -> float:
    if value <= low:
        return score_low
    if value >= high:
        return score_high
    return score_low + (score_high - score_low) * (value - low) / (high - low)


class ValueScorer:
    """割安スコア (0-100点)
    PER 0-25, PBR 0-25, ネットキャッシュ比率 0-25, 52週高値乖離率 0-25
    """

    @staticmethod
    def score(snap: FinancialSnapshot) -> float:
        per = ValueScorer.score_per(snap.per)
        pbr = ValueScorer.score_pbr(snap.pbr)
        net_cash = ValueScorer.score_net_cash_ratio(snap.net_cash_ratio)
        discount = ValueScorer.score_52w_discount(snap.high_52w_discount)
        return per + pbr + net_cash + discount

    @staticmethod
    def score_per(per: float | None) -> float:
        """PER: 5以下=25, 15=10, 30以上=0 (線形補間)"""
        if per is None:
            return 0
        return _linear_interpolate(per, 5.0, 30.0, 25.0, 0.0)

    @staticmethod
    def score_pbr(pbr: float | None) -> float:
        """PBR: 0.5以下=25, 1.0=15, 2.0以上=0 (線形補間)"""
        if pbr is None:
            return 0
        return _linear_interpolate(pbr, 0.5, 2.0, 25.0, 0.0)

    @staticmethod
    def score_net_cash_ratio(ratio: float | None) -> float:
        """ネットキャッシュ比率: 50%以上=25, 0%=5 (線形補間)"""
        if ratio is None:
            return 0
        return _linear_interpolate(ratio, 0.0, 0.50, 5.0, 25.0)

    @staticmethod
    def score_52w_discount(discount: float | None) -> float:
        """52週高値乖離率: 30%以上下落=25, 10%下落=10, 0%=0 (線形補間)"""
        if discount is None:
            return 0
        return _linear_interpolate(discount, 0.0, 0.30, 0.0, 25.0)
