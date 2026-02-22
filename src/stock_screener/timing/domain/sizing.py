from __future__ import annotations

from stock_screener.timing.domain.config import LOT_SIZE, MAX_CONCENTRATION, MIN_CASH_RESERVE
from stock_screener.timing.domain.portfolio import Portfolio


def check_sizing(
    ticker: str,
    current_price: float,
    portfolio: Portfolio,
) -> tuple[str, str]:
    """サイジング判定 C1-C3 を実行する。

    Returns:
        ("pass", message) or ("skip", message)
    """
    if current_price <= 0:
        msg = f"current_price は正の値である必要があります: {current_price}"
        raise ValueError(msg)

    required = current_price * LOT_SIZE

    # C1: 資金不足
    if required > portfolio.cash_balance:
        return ("skip", f"C1: 資金不足 (必要={required:,.0f}, 現金={portfolio.cash_balance:,.0f})")

    # C2: 集中度超過
    if required > portfolio.total_capital * MAX_CONCENTRATION:
        limit = portfolio.total_capital * MAX_CONCENTRATION
        return ("skip", f"C2: 集中度超過 (必要={required:,.0f}, 上限={limit:,.0f})")

    # C3: 余力不足
    remaining_cash = portfolio.cash_balance - required
    min_reserve = portfolio.total_capital * MIN_CASH_RESERVE
    if remaining_cash < min_reserve:
        return ("skip", f"C3: 余力不足 (残={remaining_cash:,.0f}, 最低={min_reserve:,.0f})")

    return ("pass", f"サイジングOK ({ticker}: {LOT_SIZE}株 × {current_price:,.0f}円 = {required:,.0f}円)")
