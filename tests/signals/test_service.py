from __future__ import annotations

import numpy as np
import pandas as pd

from stock_screener.signals.service import compute_signals


def _make_history(close: list[float], volume: list[float] | None = None) -> pd.DataFrame:
    n = len(close)
    if volume is None:
        volume = [10000.0] * n
    return pd.DataFrame({"Close": close, "Volume": volume})


def _make_downtrend_then_recovery() -> pd.DataFrame:
    """60 days: 40 days down from 1000 to 700, then 20 days recovery to 800"""
    down = np.linspace(1000, 700, 40).tolist()
    up = np.linspace(700, 800, 20).tolist()
    prices = down + up
    vol = [5000.0] * 40 + [15000.0] * 20
    return _make_history(prices, vol)


class TestComputeSignals:
    def test_returns_dict_with_bottom_signal_fields(self):
        hist = _make_downtrend_then_recovery()
        result = compute_signals("5765.T", hist)
        assert result == {
            "ticker": "5765.T",
            "score": result["score"],
            "max_score": 5,
            "level": result["level"],
            "rsi_signal": result["rsi_signal"],
            "bb_signal": result["bb_signal"],
            "macd_signal": result["macd_signal"],
            "volume_confirmed": result["volume_confirmed"],
            "ma_crossover": result["ma_crossover"],
            "details": result["details"],
            "score_delta": None,
        }

    def test_details_contains_indicator_values(self):
        hist = _make_downtrend_then_recovery()
        result = compute_signals("5765.T", hist)
        assert "rsi" in result["details"]
        assert "bb_position" in result["details"]
        assert "macd_histogram" in result["details"]
        assert "volume_ratio" in result["details"]

    def test_insufficient_data_score_zero_and_level_none(self):
        hist = _make_history([100.0, 101.0, 102.0])
        result = compute_signals("5765.T", hist)
        assert result["score"] == 0
        assert result["level"] is None

    def test_volume_threshold_propagates(self):
        hist = _make_downtrend_then_recovery()
        result_high = compute_signals("5765.T", hist, volume_threshold=100.0)
        assert result_high["volume_confirmed"] is False

        result_low = compute_signals("5765.T", hist, volume_threshold=0.1)
        assert result_low["volume_confirmed"] is True

    def test_score_delta_is_none_without_previous_score(self):
        """service は previous_score を渡さないため、score_delta は常に None になる"""
        hist = _make_downtrend_then_recovery()
        result = compute_signals("5765.T", hist)
        assert result["score_delta"] is None
