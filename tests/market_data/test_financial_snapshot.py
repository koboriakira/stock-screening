import pytest

from stock_screener.market_data.domain.financial_snapshot import FinancialSnapshot


class TestFinancialSnapshot:
    def test_create_with_all_values(self):
        snap = FinancialSnapshot(
            market_cap=35_000_000_000,
            per=10.5,
            pbr=1.2,
            roe=0.12,
            operating_margin=0.09,
            revenue_growth=0.08,
            operating_profit_growth=0.15,
            equity_ratio=0.45,
            dividend_yield=0.028,
            high_52w_discount=0.15,
            net_cash_ratio=0.30,
            current_price=2800,
            avg_trading_value=150_000_000,
        )
        assert snap.per == 10.5
        assert snap.pbr == 1.2
        assert snap.market_cap == 35_000_000_000

    def test_create_with_none_values(self):
        snap = FinancialSnapshot()
        assert snap.per is None
        assert snap.pbr is None
        assert snap.market_cap is None

    def test_partial_values(self):
        snap = FinancialSnapshot(per=15.0, pbr=0.8)
        assert snap.per == 15.0
        assert snap.pbr == 0.8
        assert snap.roe is None

    def test_immutable(self):
        snap = FinancialSnapshot(per=10.0)
        with pytest.raises(AttributeError):
            snap.per = 20.0
