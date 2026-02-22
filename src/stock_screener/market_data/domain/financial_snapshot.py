from __future__ import annotations

from dataclasses import dataclass, field

# Scoring-relevant fields (used for data completeness calculation)
_SCORING_FIELDS: list[str] = [
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
class FinancialSnapshot:
    """Immutable financial snapshot for a security.

    Each field defaults to None when data is unavailable.
    """

    market_cap: float | None = field(default=None)
    per: float | None = field(default=None)
    pbr: float | None = field(default=None)
    roe: float | None = field(default=None)
    operating_margin: float | None = field(default=None)
    revenue_growth: float | None = field(default=None)
    operating_profit_growth: float | None = field(default=None)
    equity_ratio: float | None = field(default=None)
    dividend_yield: float | None = field(default=None)
    high_52w_discount: float | None = field(default=None)
    net_cash_ratio: float | None = field(default=None)
    current_price: float | None = field(default=None)
    avg_trading_value: float | None = field(default=None)

    @property
    def data_completeness(self) -> float:
        """Ratio of non-None scoring fields (0.0 to 1.0)."""
        total = len(_SCORING_FIELDS)
        present = sum(1 for f in _SCORING_FIELDS if getattr(self, f) is not None)
        return present / total if total > 0 else 0.0

    @property
    def missing_fields(self) -> list[str]:
        """List of scoring field names that are None."""
        return [f for f in _SCORING_FIELDS if getattr(self, f) is None]
