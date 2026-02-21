from __future__ import annotations

from dataclasses import dataclass, field

from stock_screener.market_data.domain.financial_snapshot import FinancialSnapshot
from stock_screener.shared.types import Ticker


@dataclass
class Security:
    """証券銘柄を表すドメインモデル。

    ティッカー、企業名、セクター、および財務スナップショットを保持する。
    financial_snapshot は後から設定されるため、ミュータブルなフィールドとしている。
    """
    ticker: Ticker
    company_name: str
    sector: str
    financial_snapshot: FinancialSnapshot = field(default_factory=FinancialSnapshot)
