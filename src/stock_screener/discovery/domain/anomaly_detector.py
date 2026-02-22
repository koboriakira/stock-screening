"""Anomaly detection for screening results."""

from __future__ import annotations

from dataclasses import dataclass

from stock_screener.discovery.domain.diff_report import ScreeningResultSnapshot
from stock_screener.market_data.domain.financial_snapshot import FinancialSnapshot
from stock_screener.shared.config import (
    ANOMALY_DOMAIN_RULES,
    ANOMALY_IQR_MULTIPLIER,
    ANOMALY_SCORE_CHANGE_THRESHOLD,
)

_IQR_TARGET_FIELDS = ("per", "pbr", "roe", "operating_margin", "net_cash_ratio", "high_52w_discount")
_MIN_IQR_SAMPLES = 4


@dataclass(frozen=True)
class AnomalyFlag:
    """Anomaly flag for a single financial metric."""

    field: str
    value: float
    rule: str  # "iqr_outlier" | "domain_range" | "score_change"
    detail: str


class AnomalyDetector:
    """Detect anomalous values in financial data."""

    def check_domain_rules(self, snapshot: FinancialSnapshot) -> list[AnomalyFlag]:
        """Check financial values against domain knowledge range rules.

        Returns a list of AnomalyFlag for values outside acceptable ranges.
        """
        flags: list[AnomalyFlag] = []
        for field, bounds in ANOMALY_DOMAIN_RULES.items():
            value = getattr(snapshot, field, None)
            if value is None:
                continue
            min_val = bounds["min"]
            max_val = bounds["max"]
            if value < min_val:
                flags.append(
                    AnomalyFlag(
                        field=field,
                        value=value,
                        rule="domain_range",
                        detail=f"{field} {value} < min {min_val}",
                    ),
                )
            elif value > max_val:
                flags.append(
                    AnomalyFlag(
                        field=field,
                        value=value,
                        rule="domain_range",
                        detail=f"{field} {value} > max {max_val}",
                    ),
                )
        return flags

    def check_iqr_outliers(
        self,
        snapshot: FinancialSnapshot,
        universe: list[FinancialSnapshot],
    ) -> list[AnomalyFlag]:
        """Check if snapshot values are IQR outliers relative to universe.

        Uses Q1 - 3.0*IQR and Q3 + 3.0*IQR as bounds.
        Requires at least 4 non-None values in universe to compute IQR.
        """
        flags: list[AnomalyFlag] = []
        for field in _IQR_TARGET_FIELDS:
            target_value = getattr(snapshot, field, None)
            if target_value is None:
                continue
            values = sorted(
                v
                for s in universe
                if (v := getattr(s, field, None)) is not None
            )
            if len(values) < _MIN_IQR_SAMPLES:
                continue
            q1, q3 = _percentile(values, 0.25), _percentile(values, 0.75)
            iqr = q3 - q1
            lower = q1 - ANOMALY_IQR_MULTIPLIER * iqr
            upper = q3 + ANOMALY_IQR_MULTIPLIER * iqr
            if target_value < lower:
                flags.append(
                    AnomalyFlag(
                        field=field,
                        value=target_value,
                        rule="iqr_outlier",
                        detail=f"{field} {target_value:.4f} < IQR lower {lower:.4f}",
                    ),
                )
            elif target_value > upper:
                flags.append(
                    AnomalyFlag(
                        field=field,
                        value=target_value,
                        rule="iqr_outlier",
                        detail=f"{field} {target_value:.4f} > IQR upper {upper:.4f}",
                    ),
                )
        return flags

    def check_score_changes(
        self,
        current_scores: dict[str, float],
        previous: ScreeningResultSnapshot | None,
    ) -> dict[str, list[AnomalyFlag]]:
        """Detect significant score changes compared to previous screening.

        Args:
            current_scores: Mapping of ticker symbol to current total score.
            previous: Previous screening snapshot, or None if unavailable.

        Returns:
            Mapping of ticker to list of AnomalyFlag for significant changes.
        """
        if previous is None:
            return {}

        prev_scores = {c.ticker: c.score_total for c in previous.candidates}
        result: dict[str, list[AnomalyFlag]] = {}

        for ticker, current_score in current_scores.items():
            prev_score = prev_scores.get(ticker)
            if prev_score is None:
                continue
            delta = current_score - prev_score
            if abs(delta) >= ANOMALY_SCORE_CHANGE_THRESHOLD:
                sign = "+" if delta > 0 else ""
                result[ticker] = [
                    AnomalyFlag(
                        field="score_total",
                        value=current_score,
                        rule="score_change",
                        detail=f"score {prev_score:.1f} -> {current_score:.1f} ({sign}{delta:.1f})",
                    ),
                ]
        return result


def _percentile(sorted_values: list[float], p: float) -> float:
    """Compute p-th percentile from sorted list using linear interpolation."""
    n = len(sorted_values)
    idx = p * (n - 1)
    lo = int(idx)
    hi = min(lo + 1, n - 1)
    frac = idx - lo
    return sorted_values[lo] * (1 - frac) + sorted_values[hi] * frac
