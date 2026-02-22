from datetime import date

from stock_screener.timing.domain.portfolio import Holding, Portfolio, TradeRecord
from stock_screener.timing.infrastructure.portfolio_repository import PortfolioRepository


class TestPortfolioRepository:
    def test_load_returns_empty_portfolio_when_file_missing(self, tmp_path):
        repo = PortfolioRepository(base_dir=tmp_path)
        portfolio = repo.load()
        assert portfolio.total_capital == 0
        assert portfolio.cash_balance == 0
        assert portfolio.holdings == []
        assert portfolio.history == []

    def test_save_and_load_roundtrip(self, tmp_path):
        repo = PortfolioRepository(base_dir=tmp_path)
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
        portfolio = Portfolio(
            total_capital=1_000_000,
            cash_balance=822_000,
            holdings=[h],
            history=[record],
        )
        repo.save(portfolio)

        loaded = repo.load()
        assert loaded.total_capital == 1_000_000
        assert loaded.cash_balance == 822_000
        assert len(loaded.holdings) == 1
        assert loaded.holdings[0].ticker == "5599.T"
        assert loaded.holdings[0].signals_at_entry == ["S1", "S2"]
        assert len(loaded.history) == 1
        assert loaded.history[0].reason == "SIGNAL_BUY"

    def test_save_creates_directory(self, tmp_path):
        nested_dir = tmp_path / "nested" / "dir"
        repo = PortfolioRepository(base_dir=nested_dir)
        portfolio = Portfolio(total_capital=500_000, cash_balance=500_000)
        repo.save(portfolio)

        loaded = repo.load()
        assert loaded.total_capital == 500_000

    def test_save_overwrites_existing(self, tmp_path):
        repo = PortfolioRepository(base_dir=tmp_path)

        p1 = Portfolio(total_capital=1_000_000, cash_balance=1_000_000)
        repo.save(p1)

        p2 = Portfolio(total_capital=2_000_000, cash_balance=2_000_000)
        repo.save(p2)

        loaded = repo.load()
        assert loaded.total_capital == 2_000_000
