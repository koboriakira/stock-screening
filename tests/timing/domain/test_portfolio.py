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

    def test_new_fields_default_values(self):
        """新フィールドはデフォルト値で後方互換性を保つ"""
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
        assert h.trailing_count == 0
        assert h.extension_count == 0
        assert h.force_sell_flag is False
        assert h.force_sell_reason is None

    def test_new_fields_explicit_values(self):
        """新フィールドを明示的に指定できる"""
        h = Holding(
            ticker="5599.T",
            name="S&J",
            shares=100,
            entry_price=1780,
            entry_date=date(2026, 1, 15),
            stop_loss=1513,
            target_price=2670,
            max_holding_date=date(2026, 7, 14),
            trailing_count=2,
            extension_count=1,
            force_sell_flag=True,
            force_sell_reason="Gate1再評価でREJECT",
        )
        assert h.trailing_count == 2
        assert h.extension_count == 1
        assert h.force_sell_flag is True
        assert h.force_sell_reason == "Gate1再評価でREJECT"

    def test_new_fields_roundtrip(self):
        """新フィールドのシリアライズ/デシリアライズ"""
        h = Holding(
            ticker="5599.T",
            name="S&J",
            shares=100,
            entry_price=1780,
            entry_date=date(2026, 1, 15),
            stop_loss=1513,
            target_price=2670,
            max_holding_date=date(2026, 7, 14),
            trailing_count=1,
            extension_count=2,
            force_sell_flag=True,
            force_sell_reason="不正会計検出",
        )
        d = h.to_dict()
        restored = Holding.from_dict(d)
        assert restored.trailing_count == 1
        assert restored.extension_count == 2
        assert restored.force_sell_flag is True
        assert restored.force_sell_reason == "不正会計検出"

    def test_from_dict_backward_compatible(self):
        """旧形式のdictからも新フィールドがデフォルト値で復元される"""
        d = {
            "ticker": "5599.T",
            "name": "S&J",
            "shares": 100,
            "entry_price": 1780,
            "entry_date": "2026-01-15",
            "stop_loss": 1513,
            "target_price": 2670,
            "max_holding_date": "2026-07-14",
        }
        h = Holding.from_dict(d)
        assert h.trailing_count == 0
        assert h.extension_count == 0
        assert h.force_sell_flag is False
        assert h.force_sell_reason is None

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
