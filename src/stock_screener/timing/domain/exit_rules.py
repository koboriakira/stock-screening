from __future__ import annotations

from datetime import date, timedelta

from stock_screener.timing.domain.config import (
    EXTENSION_DAYS,
    MAX_HOLDING_DAYS,
    STOP_LOSS_PCT,
    TARGET_GAIN_PCT,
    TRAILING_STEP_PCT,
)
from stock_screener.timing.domain.portfolio import Holding


def calc_stop_loss(entry_price: float) -> float:
    """entry_price * (1 - STOP_LOSS_PCT)"""
    return entry_price * (1 - STOP_LOSS_PCT)


def calc_target_price(entry_price: float, trailing_count: int = 0) -> float:
    """entry_price * (1 + TARGET_GAIN_PCT + TRAILING_STEP_PCT * trailing_count)"""
    return entry_price * (1 + TARGET_GAIN_PCT + TRAILING_STEP_PCT * trailing_count)


def calc_max_holding_date(entry_date: date, extension_count: int = 0) -> date:
    """entry_date + MAX_HOLDING_DAYS + EXTENSION_DAYS * extension_count"""
    return entry_date + timedelta(days=MAX_HOLDING_DAYS + EXTENSION_DAYS * extension_count)


def check_exit_conditions(
    holding: Holding,
    current_price: float,
    today: date,
) -> dict:
    """保有中チェック(日次実行)。

    Returns:
        {
            "ticker": str,
            "action": "hold|stop_loss|target_hit|time_stop",
            "reason": str,
            "current_price": float,
            "unrealized_pnl": float,
            "unrealized_pnl_pct": float,
        }
    """
    unrealized_pnl = (current_price - holding.entry_price) * holding.shares
    unrealized_pnl_pct = (current_price - holding.entry_price) / holding.entry_price
    days_held = (today - holding.entry_date).days

    # 判定優先順: force_sell > stop_loss > time_stop > target_hit > hold
    if holding.force_sell_flag:
        action = "force_sell"
        reason = f"強制売却: {holding.force_sell_reason or '理由未指定'}"
    elif current_price <= holding.stop_loss:
        action = "stop_loss"
        reason = f"損切り: {current_price} <= {holding.stop_loss}"
    elif today >= holding.max_holding_date:
        action = "time_stop"
        reason = f"時間軸ストップ: {today} >= {holding.max_holding_date}"
    elif current_price >= holding.target_price:
        action = "target_hit"
        reason = f"利確到達: {current_price} >= {holding.target_price}"
    else:
        action = "hold"
        reason = "保有継続"

    return {
        "ticker": holding.ticker,
        "action": action,
        "reason": reason,
        "current_price": current_price,
        "unrealized_pnl": unrealized_pnl,
        "unrealized_pnl_pct": unrealized_pnl_pct,
        "name": holding.name,
        "entry_price": holding.entry_price,
        "shares": holding.shares,
        "days_held": days_held,
        "stop_loss": holding.stop_loss,
        "target_price": holding.target_price,
        "max_holding_date": holding.max_holding_date.isoformat(),
    }
