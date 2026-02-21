from decimal import Decimal

import pytest

from stock_screener.shared.types import Money, Percentage, Ticker


class TestTicker:
    def test_create_with_4digit_code(self):
        t = Ticker("7203")
        assert t.code == "7203"
        assert t.symbol == "7203.T"

    def test_create_with_5digit_code(self):
        t = Ticker("25935")
        assert t.code == "25935"
        assert t.symbol == "25935.T"

    def test_create_with_suffix(self):
        t = Ticker("7203.T")
        assert t.code == "7203"
        assert t.symbol == "7203.T"

    def test_create_with_5digit_suffix(self):
        t = Ticker("25935.T")
        assert t.code == "25935"
        assert t.symbol == "25935.T"

    def test_invalid_code_non_numeric(self):
        with pytest.raises(ValueError, match="4-5桁の数字"):
            Ticker("AAPL")

    def test_invalid_code_wrong_length(self):
        with pytest.raises(ValueError, match="4-5桁の数字"):
            Ticker("123")

    def test_equality(self):
        assert Ticker("7203") == Ticker("7203.T")

    def test_hashable(self):
        s = {Ticker("7203"), Ticker("7203.T")}
        assert len(s) == 1

    def test_str(self):
        assert str(Ticker("7203")) == "7203.T"


class TestMoney:
    def test_create_yen(self):
        m = Money.yen(1_000_000)
        assert m.amount == Decimal(1000000)

    def test_add(self):
        result = Money.yen(100) + Money.yen(200)
        assert result.amount == Decimal(300)

    def test_sub(self):
        result = Money.yen(300) - Money.yen(100)
        assert result.amount == Decimal(200)

    def test_mul(self):
        result = Money.yen(100) * 3
        assert result.amount == Decimal(300)

    def test_truediv(self):
        result = Money.yen(300) / 3
        assert result.amount == Decimal(100)

    def test_comparison(self):
        assert Money.yen(100) < Money.yen(200)
        assert Money.yen(200) > Money.yen(100)
        assert Money.yen(100) <= Money.yen(100)
        assert Money.yen(100) >= Money.yen(100)
        assert Money.yen(100) == Money.yen(100)

    def test_negative_allowed(self):
        m = Money.yen(-50_000)
        assert m.amount == Decimal(-50000)

    def test_immutable(self):
        m = Money.yen(100)
        with pytest.raises(AttributeError):
            m.amount = Decimal(200)

    def test_str(self):
        assert "1,000,000" in str(Money.yen(1_000_000))


class TestPercentage:
    def test_from_ratio(self):
        p = Percentage(Decimal("0.10"))
        assert p.to_percent() == pytest.approx(10.0)

    def test_from_percent(self):
        p = Percentage.from_percent(10.0)
        assert p.value == Decimal("0.10")

    def test_zero(self):
        p = Percentage.from_percent(0)
        assert p.value == Decimal(0)

    def test_over_100(self):
        p = Percentage.from_percent(150.0)
        assert p.to_percent() == pytest.approx(150.0)

    def test_negative(self):
        p = Percentage.from_percent(-30.0)
        assert p.to_percent() == pytest.approx(-30.0)

    def test_immutable(self):
        p = Percentage.from_percent(10.0)
        with pytest.raises(AttributeError):
            p.value = Decimal("0.5")

    def test_str(self):
        p = Percentage.from_percent(10.5)
        assert "10.5%" in str(p)
