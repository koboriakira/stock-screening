"""Anomaly detection for screening results."""

from __future__ import annotations

from dataclasses import dataclass

from stock_screener.market_data.domain.financial_snapshot import FinancialSnapshot
from stock_screener.shared.config import ANOMALY_DOMAIN_RULES


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
