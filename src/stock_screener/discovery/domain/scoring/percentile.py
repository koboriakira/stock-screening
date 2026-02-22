"""ユニバース内パーセンタイル計算モジュール。

Computes relative points (percentile) for hybrid scoring mode.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from stock_screener.market_data.domain.financial_snapshot import FinancialSnapshot

# Inverted metrics: lower value = better (cheaper)
_INVERTED_METRICS: set[str] = {"per", "pbr"}

# パーセンタイル計算対象の指標一覧
_METRIC_FIELDS: list[str] = [
    "per",
    "pbr",
    "net_cash_ratio",
    "high_52w_discount",
    "roe",
    "operating_margin",
    "equity_ratio",
    "revenue_growth",
    "operating_profit_growth",
    "dividend_yield",
]


@dataclass(frozen=True)
class UniverseStats:
    """ユニバースの統計情報。各指標のソート済みリストを保持する。"""

    sorted_values: dict[str, list[float]] = field(default_factory=dict)

    def percentile(self, metric: str, value: float | None) -> float:
        """指定した指標の値がユニバース内でどの位置にあるかを0.0〜1.0で返す。

        - 値がNoneの場合: 0.0
        - ユニバースが空の場合: 0.0
        - Inverted metrics (PER, PBR): lower value = higher percentile
        """
        if value is None:
            return 0.0

        values = self.sorted_values.get(metric, [])
        if not values:
            return 0.0

        n = len(values)
        if n == 1:
            return 0.5

        inverted = metric in _INVERTED_METRICS

        # 自分より劣る値の数をカウント
        # inverted: count values greater than current (= more expensive)
        # normal: count values less than current
        count_below = sum(1 for v in values if v > value) if inverted else sum(1 for v in values if v < value)

        return count_below / (n - 1) if n > 1 else 0.0


class PercentileCalculator:
    """FinancialSnapshotのリストからUniverseStatsを算出する。"""

    @staticmethod
    def compute(snapshots: list[FinancialSnapshot]) -> UniverseStats:
        """スナップショット群から各指標のソート済みリストを構築する。"""
        sorted_values: dict[str, list[float]] = {}

        for metric in _METRIC_FIELDS:
            values = []
            for snap in snapshots:
                v = getattr(snap, metric, None)
                if v is not None:
                    values.append(v)
            values.sort()
            sorted_values[metric] = values

        return UniverseStats(sorted_values=sorted_values)
