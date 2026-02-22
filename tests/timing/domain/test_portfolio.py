from datetime import date

from stock_screener.timing.domain.portfolio import Holding, Portfolio, TradeRecord


class TestHolding:
    def test_create_holding(self):
        h = Holding(
            ticker="5599.T",
            name="S&J",
            shares=100,
            entry_price=1780,
            entry_date=date(2026, 1, 15),
            stop_loss=1513,
            target_price=2670,
            max_holding_date=date(2026, 7, 14),
            signals_at_entry=["S1", "S2"],
            signal_score=2,
        )
        assert h.ticker == "5599.T"
        assert h.name == "S&J"
        assert h.shares == 100
        assert h.entry_price == 1780
        assert h.entry_date == date(2026, 1, 15)
        assert h.stop_loss == 1513
        assert h.target_price == 2670
        assert h.max_holding_date == date(2026, 7, 14)
        assert h.signals_at_entry == ["S1", "S2"]
        assert h.signal_score == 2

    def test_holding_is_frozen(self):
        h = Holding(
            ticker="5599.T",
            name="S&J",
            shares=100,
            entry_price=1780,
            entry_date=date(2026, 1, 15),
            stop_loss=1513,
            target_price=2670,
            max_holding_date=date(2026, 7, 14),
        )
        try:
            h.shares = 200  # type: ignore[misc]
            msg = "Expected FrozenInstanceError"
            raise AssertionError(msg)
        except AttributeError:
            pass


class TestTradeRecord:
    def test_create_buy_record(self):
        r = TradeRecord(
            action="buy",
            ticker="5599.T",
            shares=100,
            price=1780,
            date=date(2026, 1, 15),
            reason="SIGNAL_BUY",
        )
        assert r.action == "buy"
        assert r.ticker == "5599.T"
        assert r.shares == 100
        assert r.price == 1780
        assert r.date == date(2026, 1, 15)
        assert r.reason == "SIGNAL_BUY"

    def test_create_sell_record(self):
        r = TradeRecord(
            action="sell",
            ticker="5599.T",
            shares=100,
            price=1513,
            date=date(2026, 3, 1),
            reason="STOP_LOSS",
        )
        assert r.action == "sell"
        assert r.reason == "STOP_LOSS"


class TestPortfolio:
    def test_create_empty_portfolio(self):
        p = Portfolio(total_capital=1_000_000, cash_balance=1_000_000)
        assert p.total_capital == 1_000_000
        assert p.cash_balance == 1_000_000
        assert p.holdings == []
        assert p.history == []

    def test_create_portfolio_with_holdings(self):
        h = Holding(
            ticker="5599.T",
            name="S&J",
            shares=100,
            entry_price=1780,
            entry_date=date(2026, 1, 15),
            stop_loss=1513,
            target_price=2670,
            max_holding_date=date(2026, 7, 14),
        )
        p = Portfolio(
            total_capital=1_000_000,
            cash_balance=822_000,
            holdings=[h],
        )
        assert len(p.holdings) == 1
        assert p.holdings[0].ticker == "5599.T"

    def test_find_holding_by_ticker(self):
        h = Holding(
            ticker="5599.T",
            name="S&J",
            shares=100,
            entry_price=1780,
            entry_date=date(2026, 1, 15),
            stop_loss=1513,
            target_price=2670,
            max_holding_date=date(2026, 7, 14),
        )
        p = Portfolio(
            total_capital=1_000_000,
            cash_balance=822_000,
            holdings=[h],
        )
        found = p.find_holding("5599.T")
        assert found is not None
        assert found.ticker == "5599.T"

    def test_find_holding_not_found(self):
        p = Portfolio(total_capital=1_000_000, cash_balance=1_000_000)
        assert p.find_holding("9999.T") is None

    def test_to_dict_roundtrip(self):
        h = Holding(
            ticker="5599.T",
            name="S&J",
            shares=100,
            entry_price=1780,
            entry_date=date(2026, 1, 15),
            stop_loss=1513,
            target_price=2670,
            max_holding_date=date(2026, 7, 14),
            signals_at_entry=["S1", "S2"],
            signal_score=2,
        )
        record = TradeRecord(
            action="buy",
            ticker="5599.T",
            shares=100,
            price=1780,
            date=date(2026, 1, 15),
            reason="SIGNAL_BUY",
        )
        p = Portfolio(
            total_capital=1_000_000,
            cash_balance=822_000,
            holdings=[h],
            history=[record],
        )
        d = p.to_dict()
        restored = Portfolio.from_dict(d)
        assert restored.total_capital == p.total_capital
        assert restored.cash_balance == p.cash_balance
        assert len(restored.holdings) == 1
        assert restored.holdings[0].ticker == "5599.T"
        assert restored.holdings[0].signals_at_entry == ["S1", "S2"]
        assert len(restored.history) == 1
        assert restored.history[0].action == "buy"
