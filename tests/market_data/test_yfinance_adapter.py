from unittest.mock import MagicMock, patch

from stock_screener.market_data.infrastructure.yfinance_adapter import YFinanceSecurityRepository
from stock_screener.shared.types import Ticker


def _make_mock_ticker_info() -> dict:
    return {
        "marketCap": 15_000_000_000,
        "trailingPE": 12.5,
        "forwardPE": 10.0,
        "priceToBook": 0.9,
        "returnOnEquity": 0.12,
        "operatingMargins": 0.08,
        "revenueGrowth": 0.15,
        "dividendYield": 0.03,
        "currentPrice": 1500,
        "fiftyTwoWeekHigh": 2000,
        "averageVolume": 500_000,
    }


class TestYFinanceSecurityRepository:
    def test_get_financial_snapshot(self):
        mock_info = _make_mock_ticker_info()
        mock_yf_ticker = MagicMock()
        mock_yf_ticker.info = mock_info

        with patch("yfinance.Ticker", return_value=mock_yf_ticker):
            repo = YFinanceSecurityRepository()
            snapshot = repo.get_financial_snapshot(Ticker("7203"))

        assert snapshot.per == 10.0  # forwardPE preferred
        assert snapshot.pbr == 0.9
        assert snapshot.roe == 0.12
        assert snapshot.market_cap == 15_000_000_000

    def test_forward_pe_preferred_over_trailing(self):
        mock_info = _make_mock_ticker_info()
        mock_yf_ticker = MagicMock()
        mock_yf_ticker.info = mock_info

        with patch("yfinance.Ticker", return_value=mock_yf_ticker):
            repo = YFinanceSecurityRepository()
            snapshot = repo.get_financial_snapshot(Ticker("7203"))

        assert snapshot.per == 10.0

    def test_fallback_to_trailing_pe(self):
        mock_info = _make_mock_ticker_info()
        mock_info["forwardPE"] = None
        mock_yf_ticker = MagicMock()
        mock_yf_ticker.info = mock_info

        with patch("yfinance.Ticker", return_value=mock_yf_ticker):
            repo = YFinanceSecurityRepository()
            snapshot = repo.get_financial_snapshot(Ticker("7203"))

        assert snapshot.per == 12.5

    def test_missing_data_returns_none(self):
        mock_yf_ticker = MagicMock()
        mock_yf_ticker.info = {}

        with patch("yfinance.Ticker", return_value=mock_yf_ticker):
            repo = YFinanceSecurityRepository()
            snapshot = repo.get_financial_snapshot(Ticker("9999"))

        assert snapshot.per is None
        assert snapshot.pbr is None
        assert snapshot.roe is None

    def test_52w_discount_calculation(self):
        mock_info = _make_mock_ticker_info()
        # currentPrice=1500, fiftyTwoWeekHigh=2000 => discount = (2000-1500)/2000 = 0.25
        mock_yf_ticker = MagicMock()
        mock_yf_ticker.info = mock_info

        with patch("yfinance.Ticker", return_value=mock_yf_ticker):
            repo = YFinanceSecurityRepository()
            snapshot = repo.get_financial_snapshot(Ticker("7203"))

        assert snapshot.high_52w_discount is not None
        assert abs(snapshot.high_52w_discount - 0.25) < 0.01

    def test_avg_trading_value_calculation(self):
        mock_info = _make_mock_ticker_info()
        # currentPrice=1500, averageVolume=500000 => avg_value = 750_000_000
        mock_yf_ticker = MagicMock()
        mock_yf_ticker.info = mock_info

        with patch("yfinance.Ticker", return_value=mock_yf_ticker):
            repo = YFinanceSecurityRepository()
            snapshot = repo.get_financial_snapshot(Ticker("7203"))

        assert snapshot.avg_trading_value is not None
        assert snapshot.avg_trading_value == 750_000_000
