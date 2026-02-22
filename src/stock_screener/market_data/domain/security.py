from __future__ import annotations

from dataclasses import dataclass, field

from stock_screener.market_data.domain.financial_snapshot import FinancialSnapshot
from stock_screener.shared.types import Ticker


@dataclass
class Security:
    """Security domain model.

    Holds ticker, company name, sector, market category, and financial snapshot.
    financial_snapshot is mutable as it is populated after construction.
    """

    ticker: Ticker
    company_name: str
    sector: str
    market: str = ""
    financial_snapshot: FinancialSnapshot = field(default_factory=FinancialSnapshot)
