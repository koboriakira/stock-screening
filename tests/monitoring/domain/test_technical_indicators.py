import numpy as np
import pandas as pd

from stock_screener.monitoring.domain.technical_indicators import (
    calc_bollinger_bands,
    calc_macd,
    calc_rsi,
    calc_volume_ratio,
)


def _make_prices(values: list[float]) -> pd.Series:
    return pd.Series(values, dtype=float)


class TestCalcRSI:
    def test_rsi_returns_series(self):
        prices = _make_prices([100 + i for i in range(20)])
        rsi = calc_rsi(prices, period=14)
        assert isinstance(rsi, pd.Series)
        assert len(rsi) == len(prices)

    def test_rsi_all_up_near_100(self):
        """All prices going up -> RSI near 100"""
        prices = _make_prices([100 + i * 10 for i in range(20)])
        rsi = calc_rsi(prices, period=14)
        assert rsi.iloc[-1] > 90

    def test_rsi_all_down_near_0(self):
        """All prices going down -> RSI near 0"""
        prices = _make_prices([200 - i * 10 for i in range(20)])
        rsi = calc_rsi(prices, period=14)
        assert rsi.iloc[-1] < 10

    def test_rsi_default_period_is_14(self):
        prices = _make_prices([100 + i for i in range(20)])
        rsi = calc_rsi(prices)
        # Should not raise, default period=14
        assert not rsi.isna().all()


class TestCalcBollingerBands:
    def test_returns_three_series(self):
        prices = _make_prices([100 + i * 0.5 for i in range(30)])
        upper, middle, lower = calc_bollinger_bands(prices, period=20, num_std=2)
        assert isinstance(upper, pd.Series)
        assert isinstance(middle, pd.Series)
        assert isinstance(lower, pd.Series)

    def test_upper_gt_middle_gt_lower(self):
        prices = _make_prices([100 + i * 0.5 for i in range(30)])
        upper, middle, lower = calc_bollinger_bands(prices, period=20, num_std=2)
        # Check last valid values
        idx = upper.last_valid_index()
        assert upper.iloc[idx] > middle.iloc[idx] > lower.iloc[idx]

    def test_middle_is_sma(self):
        prices = _make_prices([100 + i for i in range(30)])
        _, middle, _ = calc_bollinger_bands(prices, period=20, num_std=2)
        expected_sma = prices.rolling(window=20).mean()
        pd.testing.assert_series_equal(middle, expected_sma)


class TestCalcMACD:
    def test_returns_three_series(self):
        prices = _make_prices([100 + i * 0.5 for i in range(40)])
        macd_line, signal_line, histogram = calc_macd(prices)
        assert isinstance(macd_line, pd.Series)
        assert isinstance(signal_line, pd.Series)
        assert isinstance(histogram, pd.Series)

    def test_histogram_is_macd_minus_signal(self):
        prices = _make_prices([100 + i * 0.5 for i in range(40)])
        macd_line, signal_line, histogram = calc_macd(prices)
        diff = macd_line - signal_line
        # Only compare where both are not NaN
        valid = ~(diff.isna() | histogram.isna())
        np.testing.assert_array_almost_equal(
            histogram[valid].values, diff[valid].values, decimal=10,
        )


class TestCalcVolumeRatio:
    def test_volume_ratio_calculation(self):
        volumes = pd.Series([100, 200, 150, 180, 170, 300], dtype=float)
        ratio = calc_volume_ratio(volumes, period=5)
        # Last value: 300 / mean(100,200,150,180,170) = 300 / 160 = 1.875
        expected = 300 / np.mean([100, 200, 150, 180, 170])
        assert abs(ratio - expected) < 0.001

    def test_volume_ratio_insufficient_data(self):
        volumes = pd.Series([100, 200], dtype=float)
        ratio = calc_volume_ratio(volumes, period=5)
        assert ratio == 0.0
