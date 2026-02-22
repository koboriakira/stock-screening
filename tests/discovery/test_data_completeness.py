"""Tests for data completeness calculation."""

from stock_screener.market_data.domain.financial_snapshot import FinancialSnapshot


class TestDataCompleteness:
    """FinancialSnapshot data completeness metrics."""

    def test_all_fields_present(self):
        """All scoring fields present = 1.0 completeness."""
        snap = FinancialSnapshot(
            per=10.0,
            pbr=0.8,
            net_cash_ratio=0.3,
            high_52w_discount=0.2,
            roe=0.10,
            operating_margin=0.08,
            equity_ratio=0.50,
            revenue_growth=0.10,
            operating_profit_growth=0.20,
            dividend_yield=0.03,
        )
        assert snap.data_completeness == 1.0
        assert snap.missing_fields == []

    def test_all_fields_missing(self):
        """All scoring fields missing = 0.0 completeness."""
        snap = FinancialSnapshot()
        assert snap.data_completeness == 0.0
        assert len(snap.missing_fields) == 10

    def test_partial_fields(self):
        """Some fields missing: completeness is a fraction."""
        snap = FinancialSnapshot(
            per=10.0,
            pbr=0.8,
            roe=0.10,
            operating_margin=0.08,
            equity_ratio=0.50,
        )
        # 5 out of 10 scoring fields present
        assert snap.data_completeness == 0.5
        assert "net_cash_ratio" in snap.missing_fields
        assert "high_52w_discount" in snap.missing_fields
        assert "revenue_growth" in snap.missing_fields
        assert "operating_profit_growth" in snap.missing_fields
        assert "dividend_yield" in snap.missing_fields

    def test_non_scoring_fields_excluded(self):
        """market_cap, current_price, avg_trading_value are not scoring fields."""
        snap = FinancialSnapshot(
            market_cap=10_000_000_000,
            current_price=1500,
            avg_trading_value=50_000_000,
        )
        # These fields don't count toward data completeness
        assert snap.data_completeness == 0.0
