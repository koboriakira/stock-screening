from datetime import date, timedelta

import pytest

from stock_screener.monitoring.domain.portfolio_updater import (
    apply_time_extension,
    apply_trailing_stop,
    record_buy,
    record_sell,
)
from stock_screener.timing.domain.portfolio import Holding, Portfolio


def _make_holding(
    trailing_count: int = 0,
    extension_count: int = 0,
) -> Holding:
    return Holding(
        ticker="5599.T",
        name="S&J",
        shares=100,
        entry_price=1780,
        entry_date=date(2026, 1, 15),
        stop_loss=1513,
        target_price=2670,
        max_holding_date=date(2026, 7, 14),
        trailing_count=trailing_count,
        extension_count=extension_count,
    )


def _make_portfolio(holding: Holding | None = None) -> Portfolio:
    holdings = [holding] if holding else [_make_holding()]
    return Portfolio(
        total_capital=1_000_000,
        cash_balance=822_000,
        holdings=holdings,
    )


class TestApplyTrailingStop:
    def test_m07_trailing_updates_target_and_count(self):
        """T-M07: trailing updates target_price and trailing_count"""
        portfolio = _make_portfolio()
        updated = apply_trailing_stop(portfolio, "5599.T")
        h = updated.find_holding("5599.T")
        assert h is not None
        assert h.trailing_count == 1
        # 1780 * (1 + 0.50 + 0.25*1) = 1780 * 1.75 = 3115
        assert h.target_price == 3115.0

    def test_trailing_second_time(self):
        """2nd trailing"""
        holding = _make_holding(trailing_count=1)
        holding = Holding(
            ticker=holding.ticker,
            name=holding.name,
            shares=holding.shares,
            entry_price=holding.entry_price,
            entry_date=holding.entry_date,
            stop_loss=holding.stop_loss,
            target_price=3115.0,
            max_holding_date=holding.max_holding_date,
            trailing_count=1,
        )
        portfolio = _make_portfolio(holding)
        updated = apply_trailing_stop(portfolio, "5599.T")
        h = updated.find_holding("5599.T")
        assert h is not None
        assert h.trailing_count == 2
        # 1780 * (1 + 0.50 + 0.25*2) = 1780 * 2.0 = 3560
        assert h.target_price == 3560.0

    def test_trailing_unknown_ticker_raises(self):
        portfolio = _make_portfolio()
        with pytest.raises(ValueError, match="Holding not found"):
            apply_trailing_stop(portfolio, "9999.T")


class TestApplyTimeExtension:
    def test_m08_extension_updates_date_and_count(self):
        """T-M08: extension updates max_holding_date and extension_count"""
        portfolio = _make_portfolio()
        updated = apply_time_extension(portfolio, "5599.T")
        h = updated.find_holding("5599.T")
        assert h is not None
        assert h.extension_count == 1
        # entry_date(2026-01-15) + 180 + 90*1 = 270 days
        expected = date(2026, 1, 15) + timedelta(days=270)
        assert h.max_holding_date == expected

    def test_extension_unknown_ticker_raises(self):
        portfolio = _make_portfolio()
        with pytest.raises(ValueError, match="Holding not found"):
            apply_time_extension(portfolio, "9999.T")


class TestRecordSell:
    def test_sell_removes_holding_and_adds_history(self):
        """sell: remove from holdings, add to history, update cash"""
        portfolio = _make_portfolio()
        updated = record_sell(
            portfolio, "5599.T", price=1513, sell_date=date(2026, 3, 1), reason="STOP_LOSS",
        )
        assert updated.find_holding("5599.T") is None
        assert len(updated.history) == 1
        assert updated.history[0].action == "sell"
        assert updated.history[0].price == 1513
        assert updated.history[0].reason == "STOP_LOSS"
        # cash += shares * price = 100 * 1513 = 151,300
        assert updated.cash_balance == 822_000 + 100 * 1513

    def test_sell_unknown_ticker_raises(self):
        portfolio = _make_portfolio()
        with pytest.raises(ValueError, match="Holding not found"):
            record_sell(portfolio, "9999.T", price=1500, sell_date=date(2026, 3, 1), reason="TEST")


class TestRecordBuy:
    def test_buy_adds_holding_and_history(self):
        """buy: add to holdings, add to history, decrease cash"""
        portfolio = Portfolio(
            total_capital=1_000_000,
            cash_balance=1_000_000,
        )
        updated = record_buy(
            portfolio,
            ticker="4486.T",
            name="ユナイトアンドグロウ",
            price=675,
            shares=100,
            buy_date=date(2026, 2, 26),
        )
        h = updated.find_holding("4486.T")
        assert h is not None
        assert h.ticker == "4486.T"
        assert h.name == "ユナイトアンドグロウ"
        assert h.shares == 100
        assert h.entry_price == 675
        assert h.entry_date == date(2026, 2, 26)
        # stop_loss = 675 * (1 - 0.15) = 573.75
        assert h.stop_loss == 573.75
        # target_price = 675 * (1 + 0.50) = 1012.5
        assert h.target_price == 1012.5
        # max_holding_date = 2026-02-26 + 180 days = 2026-08-25
        assert h.max_holding_date == date(2026, 2, 26) + timedelta(days=180)
        # history に buy レコードが追加される
        assert len(updated.history) == 1
        assert updated.history[0].action == "buy"
        assert updated.history[0].ticker == "4486.T"
        assert updated.history[0].shares == 100
        assert updated.history[0].price == 675
        # cash -= shares * price = 100 * 675 = 67,500
        assert updated.cash_balance == 1_000_000 - 100 * 675

    def test_buy_duplicate_ticker_raises(self):
        """同一ティッカーが既に保有中の場合はエラー"""
        portfolio = _make_portfolio()
        with pytest.raises(ValueError, match="Already holding"):
            record_buy(
                portfolio,
                ticker="5599.T",
                name="S&J",
                price=2000,
                shares=100,
                buy_date=date(2026, 3, 1),
            )

    def test_buy_insufficient_cash_raises(self):
        """現金残高が不足している場合はエラー"""
        portfolio = Portfolio(
            total_capital=1_000_000,
            cash_balance=10_000,
        )
        with pytest.raises(ValueError, match="Insufficient cash"):
            record_buy(
                portfolio,
                ticker="4486.T",
                name="ユナイトアンドグロウ",
                price=675,
                shares=100,
                buy_date=date(2026, 2, 26),
            )
