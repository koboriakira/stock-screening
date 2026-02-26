from __future__ import annotations

from datetime import date

from stock_screener.timing.domain.exit_rules import calc_max_holding_date, calc_target_price
from stock_screener.timing.domain.portfolio import Holding, Portfolio, TradeRecord


def apply_trailing_stop(portfolio: Portfolio, ticker: str) -> Portfolio:
    """トレイリングストップを適用し、target_price と trailing_count を更新する。"""
    holding = portfolio.find_holding(ticker)
    if holding is None:
        msg = f"Holding not found: {ticker}"
        raise ValueError(msg)

    new_count = holding.trailing_count + 1
    new_target = calc_target_price(holding.entry_price, trailing_count=new_count)

    updated_holding = Holding(
        ticker=holding.ticker,
        name=holding.name,
        shares=holding.shares,
        entry_price=holding.entry_price,
        entry_date=holding.entry_date,
        stop_loss=holding.stop_loss,
        target_price=new_target,
        max_holding_date=holding.max_holding_date,
        signals_at_entry=holding.signals_at_entry,
        signal_score=holding.signal_score,
        trailing_count=new_count,
        extension_count=holding.extension_count,
        force_sell_flag=holding.force_sell_flag,
        force_sell_reason=holding.force_sell_reason,
    )

    new_holdings = [updated_holding if h.ticker == ticker else h for h in portfolio.holdings]
    return Portfolio(
        total_capital=portfolio.total_capital,
        cash_balance=portfolio.cash_balance,
        holdings=new_holdings,
        history=list(portfolio.history),
    )


def apply_time_extension(portfolio: Portfolio, ticker: str) -> Portfolio:
    """保有期間延長を適用し、max_holding_date と extension_count を更新する。"""
    holding = portfolio.find_holding(ticker)
    if holding is None:
        msg = f"Holding not found: {ticker}"
        raise ValueError(msg)

    new_count = holding.extension_count + 1
    new_date = calc_max_holding_date(holding.entry_date, extension_count=new_count)

    updated_holding = Holding(
        ticker=holding.ticker,
        name=holding.name,
        shares=holding.shares,
        entry_price=holding.entry_price,
        entry_date=holding.entry_date,
        stop_loss=holding.stop_loss,
        target_price=holding.target_price,
        max_holding_date=new_date,
        signals_at_entry=holding.signals_at_entry,
        signal_score=holding.signal_score,
        trailing_count=holding.trailing_count,
        extension_count=new_count,
        force_sell_flag=holding.force_sell_flag,
        force_sell_reason=holding.force_sell_reason,
    )

    new_holdings = [updated_holding if h.ticker == ticker else h for h in portfolio.holdings]
    return Portfolio(
        total_capital=portfolio.total_capital,
        cash_balance=portfolio.cash_balance,
        holdings=new_holdings,
        history=list(portfolio.history),
    )


def record_buy(
    portfolio: Portfolio,
    ticker: str,
    name: str,
    price: float,
    shares: int,
    buy_date: date,
) -> Portfolio:
    """購入を記録し、holdings に追加、history に追加、cash_balance を減算する。"""
    if portfolio.find_holding(ticker) is not None:
        msg = f"Already holding: {ticker}"
        raise ValueError(msg)

    cost = shares * price
    if portfolio.cash_balance < cost:
        msg = f"Insufficient cash: {portfolio.cash_balance} < {cost}"
        raise ValueError(msg)

    from stock_screener.timing.domain.exit_rules import (  # noqa: PLC0415
        calc_max_holding_date,
        calc_stop_loss,
        calc_target_price,
    )

    holding = Holding(
        ticker=ticker,
        name=name,
        shares=shares,
        entry_price=price,
        entry_date=buy_date,
        stop_loss=calc_stop_loss(price),
        target_price=calc_target_price(price),
        max_holding_date=calc_max_holding_date(buy_date),
    )

    record = TradeRecord(
        action="buy",
        ticker=ticker,
        shares=shares,
        price=price,
        date=buy_date,
        reason="manual_entry",
    )

    return Portfolio(
        total_capital=portfolio.total_capital,
        cash_balance=portfolio.cash_balance - cost,
        holdings=[*list(portfolio.holdings), holding],
        history=[*list(portfolio.history), record],
    )


def record_sell(
    portfolio: Portfolio,
    ticker: str,
    price: float,
    sell_date: date,
    reason: str,
) -> Portfolio:
    """売却を記録し、holdings から削除、history に追加、cash_balance を加算する。"""
    holding = portfolio.find_holding(ticker)
    if holding is None:
        msg = f"Holding not found: {ticker}"
        raise ValueError(msg)

    record = TradeRecord(
        action="sell",
        ticker=ticker,
        shares=holding.shares,
        price=price,
        date=sell_date,
        reason=reason,
    )

    new_holdings = [h for h in portfolio.holdings if h.ticker != ticker]
    new_history = [*list(portfolio.history), record]
    new_cash = portfolio.cash_balance + holding.shares * price

    return Portfolio(
        total_capital=portfolio.total_capital,
        cash_balance=new_cash,
        holdings=new_holdings,
        history=new_history,
    )
