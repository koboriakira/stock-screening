from stock_screener.discovery.domain.hard_filter import HardFilter
from stock_screener.market_data.domain.financial_snapshot import FinancialSnapshot
from stock_screener.market_data.domain.security import Security
from stock_screener.shared.types import Ticker


def _make_security(
    ticker: str = "1234",
    sector: str = "電気機器",
    market_cap: float | None = 10_000_000_000,
    avg_trading_value: float | None = 50_000_000,
) -> Security:
    return Security(
        ticker=Ticker(ticker),
        company_name="テスト株式会社",
        sector=sector,
        financial_snapshot=FinancialSnapshot(
            market_cap=market_cap,
            avg_trading_value=avg_trading_value,
        ),
    )


class TestHardFilter:
    def test_passes_valid_security(self):
        securities = [_make_security()]
        result = HardFilter().apply(securities)
        assert len(result) == 1

    def test_excludes_market_cap_too_low(self):
        securities = [_make_security(market_cap=3_000_000_000)]
        result = HardFilter().apply(securities)
        assert len(result) == 0

    def test_excludes_market_cap_too_high(self):
        securities = [_make_security(market_cap=60_000_000_000)]
        result = HardFilter().apply(securities)
        assert len(result) == 0

    def test_boundary_market_cap_min(self):
        securities = [_make_security(market_cap=5_000_000_000)]
        result = HardFilter().apply(securities)
        assert len(result) == 1

    def test_boundary_market_cap_max(self):
        securities = [_make_security(market_cap=50_000_000_000)]
        result = HardFilter().apply(securities)
        assert len(result) == 1

    def test_excludes_low_trading_value(self):
        securities = [_make_security(avg_trading_value=3_000_000)]
        result = HardFilter().apply(securities)
        assert len(result) == 0

    def test_excludes_pharma_sector(self):
        securities = [_make_security(sector="医薬品")]
        result = HardFilter().apply(securities)
        assert len(result) == 0

    def test_excludes_real_estate_sector(self):
        securities = [_make_security(sector="不動産業")]
        result = HardFilter().apply(securities)
        assert len(result) == 0

    def test_excludes_none_market_cap(self):
        securities = [_make_security(market_cap=None)]
        result = HardFilter().apply(securities)
        assert len(result) == 0

    def test_excludes_none_trading_value(self):
        securities = [_make_security(avg_trading_value=None)]
        result = HardFilter().apply(securities)
        assert len(result) == 0

    def test_mixed_securities(self):
        securities = [
            _make_security(ticker="1001"),  # pass
            _make_security(ticker="1002", market_cap=1_000_000_000),  # fail: too small
            _make_security(ticker="1003", sector="医薬品"),  # fail: pharma
            _make_security(ticker="1004"),  # pass
        ]
        result = HardFilter().apply(securities)
        assert len(result) == 2
        tickers = [s.ticker.code for s in result]
        assert "1001" in tickers
        assert "1004" in tickers
