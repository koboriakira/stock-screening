from unittest.mock import MagicMock, PropertyMock, patch

import pandas as pd
import pytest
import requests

from stock_screener.market_data.infrastructure.cache import FileCache
from stock_screener.market_data.infrastructure.yfinance_adapter import (
    YFinanceSecurityRepository,
    _compute_net_cash_ratio,
    _compute_operating_profit_growth,
    _safe_get_dataframe,
)
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
        "totalCash": 5_000_000_000,
        "totalDebt": 3_000_000_000,
    }


def _make_mock_balance_sheet() -> pd.DataFrame:
    """Total Assets = 20B, Stockholders Equity = 10B のバランスシート。"""
    return pd.DataFrame(
        {"2024-03-31": [20_000_000_000, 10_000_000_000]},
        index=["Total Assets", "Stockholders Equity"],
    )


def _make_mock_financials() -> pd.DataFrame:
    """営業利益: 直近 1200, 前年 1000 → 成長率 20%。"""
    return pd.DataFrame(
        {"2024-03-31": [1_200_000_000], "2023-03-31": [1_000_000_000]},
        index=["Operating Income"],
    )


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


class TestNetCashRatio:
    """net_cash_ratio = (totalCash - totalDebt) / totalAssets."""

    def test_net_cash_ratio_computed(self):
        # cash=5B, debt=3B, totalAssets=20B => (5-3)/20 = 0.10
        mock_yf_ticker = MagicMock()
        mock_yf_ticker.info = _make_mock_ticker_info()
        type(mock_yf_ticker).balance_sheet = PropertyMock(return_value=_make_mock_balance_sheet())
        type(mock_yf_ticker).financials = PropertyMock(return_value=pd.DataFrame())

        with patch("yfinance.Ticker", return_value=mock_yf_ticker):
            repo = YFinanceSecurityRepository()
            snapshot = repo.get_financial_snapshot(Ticker("7203"))

        assert snapshot.net_cash_ratio is not None
        assert abs(snapshot.net_cash_ratio - 0.10) < 0.01

    def test_net_cash_ratio_negative(self):
        # cash=1B, debt=5B, totalAssets=20B => (1-5)/20 = -0.20
        mock_info = _make_mock_ticker_info()
        mock_info["totalCash"] = 1_000_000_000
        mock_info["totalDebt"] = 5_000_000_000
        mock_yf_ticker = MagicMock()
        mock_yf_ticker.info = mock_info
        type(mock_yf_ticker).balance_sheet = PropertyMock(return_value=_make_mock_balance_sheet())
        type(mock_yf_ticker).financials = PropertyMock(return_value=pd.DataFrame())

        with patch("yfinance.Ticker", return_value=mock_yf_ticker):
            repo = YFinanceSecurityRepository()
            snapshot = repo.get_financial_snapshot(Ticker("7203"))

        assert snapshot.net_cash_ratio is not None
        assert abs(snapshot.net_cash_ratio - (-0.20)) < 0.01

    def test_net_cash_ratio_none_when_no_total_assets(self):
        mock_yf_ticker = MagicMock()
        mock_yf_ticker.info = _make_mock_ticker_info()
        type(mock_yf_ticker).balance_sheet = PropertyMock(return_value=pd.DataFrame())
        type(mock_yf_ticker).financials = PropertyMock(return_value=pd.DataFrame())

        with patch("yfinance.Ticker", return_value=mock_yf_ticker):
            repo = YFinanceSecurityRepository()
            snapshot = repo.get_financial_snapshot(Ticker("7203"))

        assert snapshot.net_cash_ratio is None

    def test_net_cash_ratio_none_when_no_cash_info(self):
        mock_info = _make_mock_ticker_info()
        del mock_info["totalCash"]
        del mock_info["totalDebt"]
        mock_yf_ticker = MagicMock()
        mock_yf_ticker.info = mock_info
        type(mock_yf_ticker).balance_sheet = PropertyMock(return_value=_make_mock_balance_sheet())
        type(mock_yf_ticker).financials = PropertyMock(return_value=pd.DataFrame())

        with patch("yfinance.Ticker", return_value=mock_yf_ticker):
            repo = YFinanceSecurityRepository()
            snapshot = repo.get_financial_snapshot(Ticker("7203"))

        assert snapshot.net_cash_ratio is None


class TestEquityRatio:
    """equity_ratio = stockholdersEquity / totalAssets."""

    def test_equity_ratio_computed(self):
        # equity=10B, totalAssets=20B => 0.50
        mock_yf_ticker = MagicMock()
        mock_yf_ticker.info = _make_mock_ticker_info()
        type(mock_yf_ticker).balance_sheet = PropertyMock(return_value=_make_mock_balance_sheet())
        type(mock_yf_ticker).financials = PropertyMock(return_value=pd.DataFrame())

        with patch("yfinance.Ticker", return_value=mock_yf_ticker):
            repo = YFinanceSecurityRepository()
            snapshot = repo.get_financial_snapshot(Ticker("7203"))

        assert snapshot.equity_ratio is not None
        assert abs(snapshot.equity_ratio - 0.50) < 0.01

    def test_equity_ratio_none_when_no_balance_sheet(self):
        mock_yf_ticker = MagicMock()
        mock_yf_ticker.info = _make_mock_ticker_info()
        type(mock_yf_ticker).balance_sheet = PropertyMock(return_value=pd.DataFrame())
        type(mock_yf_ticker).financials = PropertyMock(return_value=pd.DataFrame())

        with patch("yfinance.Ticker", return_value=mock_yf_ticker):
            repo = YFinanceSecurityRepository()
            snapshot = repo.get_financial_snapshot(Ticker("7203"))

        assert snapshot.equity_ratio is None


class TestOperatingProfitGrowth:
    """operating_profit_growth = (直近営業利益 - 前年営業利益) / |前年営業利益|."""

    def test_growth_computed(self):
        # 1200/1000 - 1 = 0.20
        mock_yf_ticker = MagicMock()
        mock_yf_ticker.info = _make_mock_ticker_info()
        type(mock_yf_ticker).balance_sheet = PropertyMock(return_value=_make_mock_balance_sheet())
        type(mock_yf_ticker).financials = PropertyMock(return_value=_make_mock_financials())

        with patch("yfinance.Ticker", return_value=mock_yf_ticker):
            repo = YFinanceSecurityRepository()
            snapshot = repo.get_financial_snapshot(Ticker("7203"))

        assert snapshot.operating_profit_growth is not None
        assert abs(snapshot.operating_profit_growth - 0.20) < 0.01

    def test_growth_negative(self):
        # 800/1000 - 1 = -0.20
        financials = pd.DataFrame(
            {"2024-03-31": [800_000_000], "2023-03-31": [1_000_000_000]},
            index=["Operating Income"],
        )
        mock_yf_ticker = MagicMock()
        mock_yf_ticker.info = _make_mock_ticker_info()
        type(mock_yf_ticker).balance_sheet = PropertyMock(return_value=_make_mock_balance_sheet())
        type(mock_yf_ticker).financials = PropertyMock(return_value=financials)

        with patch("yfinance.Ticker", return_value=mock_yf_ticker):
            repo = YFinanceSecurityRepository()
            snapshot = repo.get_financial_snapshot(Ticker("7203"))

        assert snapshot.operating_profit_growth is not None
        assert abs(snapshot.operating_profit_growth - (-0.20)) < 0.01

    def test_turnaround_from_loss(self):
        # 前年赤字(-500) → 今期黒字(200): (200 - (-500)) / |-500| = 1.40
        financials = pd.DataFrame(
            {"2024-03-31": [200_000_000], "2023-03-31": [-500_000_000]},
            index=["Operating Income"],
        )
        mock_yf_ticker = MagicMock()
        mock_yf_ticker.info = _make_mock_ticker_info()
        type(mock_yf_ticker).balance_sheet = PropertyMock(return_value=_make_mock_balance_sheet())
        type(mock_yf_ticker).financials = PropertyMock(return_value=financials)

        with patch("yfinance.Ticker", return_value=mock_yf_ticker):
            repo = YFinanceSecurityRepository()
            snapshot = repo.get_financial_snapshot(Ticker("7203"))

        assert snapshot.operating_profit_growth is not None
        assert abs(snapshot.operating_profit_growth - 1.40) < 0.01

    def test_none_when_single_year(self):
        financials = pd.DataFrame(
            {"2024-03-31": [1_200_000_000]},
            index=["Operating Income"],
        )
        mock_yf_ticker = MagicMock()
        mock_yf_ticker.info = _make_mock_ticker_info()
        type(mock_yf_ticker).balance_sheet = PropertyMock(return_value=_make_mock_balance_sheet())
        type(mock_yf_ticker).financials = PropertyMock(return_value=financials)

        with patch("yfinance.Ticker", return_value=mock_yf_ticker):
            repo = YFinanceSecurityRepository()
            snapshot = repo.get_financial_snapshot(Ticker("7203"))

        assert snapshot.operating_profit_growth is None

    def test_none_when_no_financials(self):
        mock_yf_ticker = MagicMock()
        mock_yf_ticker.info = _make_mock_ticker_info()
        type(mock_yf_ticker).balance_sheet = PropertyMock(return_value=_make_mock_balance_sheet())
        type(mock_yf_ticker).financials = PropertyMock(return_value=pd.DataFrame())

        with patch("yfinance.Ticker", return_value=mock_yf_ticker):
            repo = YFinanceSecurityRepository()
            snapshot = repo.get_financial_snapshot(Ticker("7203"))

        assert snapshot.operating_profit_growth is None

    def test_none_when_previous_year_zero(self):
        financials = pd.DataFrame(
            {"2024-03-31": [500_000_000], "2023-03-31": [0]},
            index=["Operating Income"],
        )
        mock_yf_ticker = MagicMock()
        mock_yf_ticker.info = _make_mock_ticker_info()
        type(mock_yf_ticker).balance_sheet = PropertyMock(return_value=_make_mock_balance_sheet())
        type(mock_yf_ticker).financials = PropertyMock(return_value=financials)

        with patch("yfinance.Ticker", return_value=mock_yf_ticker):
            repo = YFinanceSecurityRepository()
            snapshot = repo.get_financial_snapshot(Ticker("7203"))

        assert snapshot.operating_profit_growth is None


class TestGetUniverseNotImplemented:
    def test_raises_not_implemented(self):
        repo = YFinanceSecurityRepository()
        with pytest.raises(NotImplementedError):
            repo.get_universe()


class TestFetchRetryFallback:
    def test_returns_empty_snapshot_when_retry_returns_none(self):
        with patch(
            "stock_screener.market_data.infrastructure.yfinance_adapter.retry_on_rate_limit",
            return_value=None,
        ):
            repo = YFinanceSecurityRepository()
            snapshot = repo.get_financial_snapshot(Ticker("9999"))

        assert snapshot.per is None
        assert snapshot.market_cap is None

    def test_returns_empty_snapshot_on_request_error(self):
        with patch(
            "stock_screener.market_data.infrastructure.yfinance_adapter.retry_on_rate_limit",
            side_effect=requests.exceptions.ConnectionError("timeout"),
        ):
            repo = YFinanceSecurityRepository()
            snapshot = repo.get_financial_snapshot(Ticker("9999"))

        assert snapshot.per is None


class TestSafeGetDataframe:
    def test_returns_empty_on_error(self):
        mock_ticker = MagicMock()
        type(mock_ticker).balance_sheet = PropertyMock(
            side_effect=requests.exceptions.ConnectionError("timeout"),
        )
        result = _safe_get_dataframe(mock_ticker, "balance_sheet")
        assert result.empty

    def test_returns_empty_when_none(self):
        mock_ticker = MagicMock()
        type(mock_ticker).balance_sheet = PropertyMock(return_value=None)
        result = _safe_get_dataframe(mock_ticker, "balance_sheet")
        assert result.empty


class TestComputeNetCashRatioEdgeCases:
    def test_returns_none_when_total_assets_zero(self):
        bs = pd.DataFrame(
            {"2024-03-31": [0, 10_000]},
            index=["Total Assets", "Stockholders Equity"],
        )
        result = _compute_net_cash_ratio(5000, 3000, bs)
        assert result is None


class TestComputeOperatingProfitGrowthEdgeCases:
    def test_returns_none_when_no_operating_income_row(self):
        financials = pd.DataFrame({"2024-03-31": [100]}, index=["Revenue"])
        result = _compute_operating_profit_growth(financials)
        assert result is None


class TestCacheIntegration:
    """FileCache とのキャッシュ統合テスト。"""

    def _make_repo_with_mock(self, tmp_path):
        mock_yf_ticker = MagicMock()
        mock_yf_ticker.info = _make_mock_ticker_info()
        type(mock_yf_ticker).balance_sheet = PropertyMock(return_value=_make_mock_balance_sheet())
        type(mock_yf_ticker).financials = PropertyMock(return_value=_make_mock_financials())
        return mock_yf_ticker

    def test_cache_hit_skips_api(self, tmp_path):
        cache = FileCache(cache_dir=tmp_path, ttl_hours=24)
        mock_yf_ticker = self._make_repo_with_mock(tmp_path)

        with patch("yfinance.Ticker", return_value=mock_yf_ticker) as mock_cls:
            repo = YFinanceSecurityRepository(cache=cache)
            # 1回目: API を呼ぶ
            snap1 = repo.get_financial_snapshot(Ticker("7203"))
            # 2回目: キャッシュから取得
            snap2 = repo.get_financial_snapshot(Ticker("7203"))

        # yfinance.Ticker は1回しか呼ばれない
        assert mock_cls.call_count == 1
        assert snap1.per == snap2.per
        assert snap1.market_cap == snap2.market_cap

    def test_different_tickers_not_shared(self, tmp_path):
        cache = FileCache(cache_dir=tmp_path, ttl_hours=24)
        mock_yf_ticker = self._make_repo_with_mock(tmp_path)

        with patch("yfinance.Ticker", return_value=mock_yf_ticker) as mock_cls:
            repo = YFinanceSecurityRepository(cache=cache)
            repo.get_financial_snapshot(Ticker("7203"))
            repo.get_financial_snapshot(Ticker("6758"))

        assert mock_cls.call_count == 2
        mock_cls.assert_any_call("7203.T")
        mock_cls.assert_any_call("6758.T")

    def test_no_cache_still_works(self):
        mock_yf_ticker = MagicMock()
        mock_yf_ticker.info = _make_mock_ticker_info()
        type(mock_yf_ticker).balance_sheet = PropertyMock(return_value=_make_mock_balance_sheet())
        type(mock_yf_ticker).financials = PropertyMock(return_value=_make_mock_financials())

        with patch("yfinance.Ticker", return_value=mock_yf_ticker):
            repo = YFinanceSecurityRepository()  # cache=None
            snapshot = repo.get_financial_snapshot(Ticker("7203"))

        assert snapshot.per == 10.0


class TestGetMarketCapOnly:
    """Lightweight market cap fetch for Stage 1."""

    def test_returns_market_cap(self):
        mock_yf_ticker = MagicMock()
        mock_yf_ticker.info = {"marketCap": 10_000_000_000}

        with patch("yfinance.Ticker", return_value=mock_yf_ticker):
            repo = YFinanceSecurityRepository()
            result = repo.get_market_cap_only(Ticker("7203"))

        assert result == 10_000_000_000

    def test_returns_none_on_error(self):
        with patch(
            "stock_screener.market_data.infrastructure.yfinance_adapter.retry_on_rate_limit",
            return_value=None,
        ):
            repo = YFinanceSecurityRepository()
            result = repo.get_market_cap_only(Ticker("9999"))

        assert result is None

    def test_uses_cache(self, tmp_path):
        cache = FileCache(cache_dir=tmp_path, ttl_hours=24)
        mock_yf_ticker = MagicMock()
        mock_yf_ticker.info = {"marketCap": 10_000_000_000}

        with patch("yfinance.Ticker", return_value=mock_yf_ticker) as mock_cls:
            repo = YFinanceSecurityRepository(cache=cache)
            result1 = repo.get_market_cap_only(Ticker("7203"))
            result2 = repo.get_market_cap_only(Ticker("7203"))

        assert mock_cls.call_count == 1
        assert result1 == result2
