from stock_screener.timing.domain.portfolio import Portfolio
from stock_screener.timing.domain.sizing import check_sizing


class TestCheckSizing:
    def test_s01_cash_insufficient(self):
        """T-S01: 資金不足 - cash=50,000, price=1,780 → skip"""
        portfolio = Portfolio(total_capital=1_000_000, cash_balance=50_000)
        result, message = check_sizing("5599.T", 1780, portfolio)
        assert result == "skip"
        assert "C1" in message

    def test_s02_concentration_exceeded(self):
        """T-S02: 集中度超過 - total=100,000, price=600 → skip (600*100=60,000 > 100,000*0.50)"""
        portfolio = Portfolio(total_capital=100_000, cash_balance=100_000)
        result, message = check_sizing("5599.T", 600, portfolio)
        assert result == "skip"
        assert "C2" in message

    def test_s03_reserve_insufficient(self):
        """T-S03: 余力不足 - cash=200,000, total=1,000,000, price=1,800
        required=180,000, remaining=20,000 < 100,000 (10%) → skip"""
        portfolio = Portfolio(total_capital=1_000_000, cash_balance=200_000)
        result, message = check_sizing("5599.T", 1800, portfolio)
        assert result == "skip"
        assert "C3" in message

    def test_s04_all_pass(self):
        """T-S04: 全PASS - cash=1,000,000, total=1,000,000, price=1,780"""
        portfolio = Portfolio(total_capital=1_000_000, cash_balance=1_000_000)
        result, _message = check_sizing("5599.T", 1780, portfolio)
        assert result == "pass"

    def test_invalid_price_zero(self):
        """price=0 → ValueError"""
        portfolio = Portfolio(total_capital=1_000_000, cash_balance=1_000_000)
        try:
            check_sizing("5599.T", 0, portfolio)
            msg = "Expected ValueError"
            raise AssertionError(msg)
        except ValueError:
            pass

    def test_invalid_price_negative(self):
        """price=-100 → ValueError"""
        portfolio = Portfolio(total_capital=1_000_000, cash_balance=1_000_000)
        try:
            check_sizing("5599.T", -100, portfolio)
            msg = "Expected ValueError"
            raise AssertionError(msg)
        except ValueError:
            pass

    def test_c1_exact_boundary_pass(self):
        """現金がちょうど必要額と等しい場合 → pass"""
        portfolio = Portfolio(total_capital=1_000_000, cash_balance=178_000)
        # C1: 1780*100=178,000 == cash → pass
        # C2: 178,000 < 500,000 → pass
        # C3: 178,000-178,000=0 < 100,000 → skip (余力不足)
        result, message = check_sizing("5599.T", 1780, portfolio)
        assert result == "skip"
        assert "C3" in message

    def test_c2_exact_boundary_pass(self):
        """required が total_capital * MAX_CONCENTRATION とちょうど等しい → pass"""
        # 500*100=50,000 == 100,000*0.50 → pass (equal is allowed)
        portfolio = Portfolio(total_capital=100_000, cash_balance=100_000)
        result, _message = check_sizing("5599.T", 500, portfolio)
        assert result == "pass"
