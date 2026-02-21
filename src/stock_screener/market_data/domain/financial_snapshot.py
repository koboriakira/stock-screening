from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class FinancialSnapshot:
    """銘柄の財務スナップショット。

    yfinance 等から取得した各種財務指標をイミュータブルに保持する。
    各フィールドはデータ未取得時に None となる。
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
