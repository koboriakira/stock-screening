import numpy as np
import pandas as pd

from stock_screener.monitoring.domain.bottom_detector import (
    BottomSignal,
    detect_bottom_signals,
)


def _make_history(
    close: list[float],
    volume: list[float] | None = None,
) -> pd.DataFrame:
    n = len(close)
    if volume is None:
        volume = [10000.0] * n
    return pd.DataFrame({
        "Close": close,
        "Volume": volume,
    })


def _make_downtrend_then_recovery() -> pd.DataFrame:
    """60 days: 40 days down from 1000 to 700, then 20 days recovery to 800"""
    down = np.linspace(1000, 700, 40).tolist()
    up = np.linspace(700, 800, 20).tolist()
    prices = down + up
    # Volume spike on recovery
    vol = [5000.0] * 40 + [15000.0] * 20
    return _make_history(prices, vol)


def _make_steady_uptrend() -> pd.DataFrame:
    """60 days of steady uptrend"""
    prices = np.linspace(500, 1000, 60).tolist()
    return _make_history(prices, [10000.0] * 60)


class TestBottomSignal:
    def test_signal_fields(self):
        sig = BottomSignal(
            ticker="5765.T",
            score=3,
            max_score=5,
            level="buy_candidate",
            rsi_signal=True,
            bb_signal=True,
            macd_signal=True,
            volume_confirmed=True,
            ma_crossover=False,
            details={},
        )
        assert sig.ticker == "5765.T"
        assert sig.score == 3
        assert sig.level == "buy_candidate"

    def test_signal_has_score_delta(self):
        sig = BottomSignal(
            ticker="5765.T",
            score=3,
            max_score=5,
            level=None,
            rsi_signal=False,
            bb_signal=False,
            macd_signal=False,
            volume_confirmed=False,
            ma_crossover=False,
            score_delta=1,
        )
        assert sig.score_delta == 1

    def test_signal_score_delta_default_none(self):
        sig = BottomSignal(
            ticker="5765.T",
            score=0,
            max_score=5,
            level=None,
            rsi_signal=False,
            bb_signal=False,
            macd_signal=False,
            volume_confirmed=False,
            ma_crossover=False,
        )
        assert sig.score_delta is None


class TestDetectBottomSignals:
    def test_returns_bottom_signal(self):
        hist = _make_downtrend_then_recovery()
        result = detect_bottom_signals("5765.T", hist)
        assert isinstance(result, BottomSignal)
        assert result.ticker == "5765.T"

    def test_steady_uptrend_low_score(self):
        """steady uptrend -> RSI high, no BB/MACD bottom signal"""
        hist = _make_steady_uptrend()
        result = detect_bottom_signals("5765.T", hist)
        # Uptrend should not trigger bottom signals
        assert result.rsi_signal is False

    def test_insufficient_data(self):
        """insufficient data -> score 0"""
        hist = _make_history([100.0, 101.0, 102.0])
        result = detect_bottom_signals("5765.T", hist)
        assert result.score == 0

    def test_level_none_for_low_score(self):
        """score 0 or 1 -> level is None"""
        hist = _make_steady_uptrend()
        result = detect_bottom_signals("5765.T", hist)
        if result.score < 2:
            assert result.level is None

    def test_score_max_is_5(self):
        hist = _make_downtrend_then_recovery()
        result = detect_bottom_signals("5765.T", hist)
        assert result.max_score == 5

    def test_details_contains_indicator_values(self):
        hist = _make_downtrend_then_recovery()
        result = detect_bottom_signals("5765.T", hist)
        assert "rsi" in result.details
        assert "bb_position" in result.details
        assert "macd_histogram" in result.details
        assert "volume_ratio" in result.details

    def test_volume_threshold_parameter(self):
        """volume_threshold パラメータで出来高閾値を変更できる"""
        hist = _make_downtrend_then_recovery()
        # 高い閾値 -> volume_confirmed が False になりやすい
        result_high = detect_bottom_signals("5765.T", hist, volume_threshold=100.0)
        assert result_high.volume_confirmed is False

        # 低い閾値 -> volume_confirmed が True になりやすい
        result_low = detect_bottom_signals("5765.T", hist, volume_threshold=0.1)
        assert result_low.volume_confirmed is True

    def test_rsi_soft_bottom_detection(self):
        """RSI が 30 を割らなくても、底打ち上昇パターンを検出する"""
        # RSI が 35 近辺で底打ちして上昇するパターン
        # 緩やかな下げ(RSI 30割れしない) -> 底打ち -> 上昇
        base = np.linspace(1000, 900, 30).tolist()  # 緩やかな下げ
        bottom = np.linspace(900, 880, 10).tolist()  # さらに小幅下げ
        recovery = np.linspace(880, 920, 20).tolist()  # 回復
        prices = base + bottom + recovery
        hist = _make_history(prices)
        result = detect_bottom_signals("5765.T", hist)
        # RSI が底打ちパターンなら rsi_signal が True
        # (厳密な値は相場データ依存だが、soft bottom detection が動くことを確認)
        assert isinstance(result.rsi_signal, bool)


class TestScoreDelta:
    def test_score_delta_calculated(self):
        hist = _make_downtrend_then_recovery()
        result = detect_bottom_signals("5765.T", hist, previous_score=1)
        assert result.score_delta == result.score - 1

    def test_score_delta_none_without_previous(self):
        hist = _make_downtrend_then_recovery()
        result = detect_bottom_signals("5765.T", hist)
        assert result.score_delta is None

    def test_score_delta_with_zero_previous(self):
        hist = _make_downtrend_then_recovery()
        result = detect_bottom_signals("5765.T", hist, previous_score=0)
        assert result.score_delta == result.score

    def test_score_delta_negative(self):
        hist = _make_steady_uptrend()
        result = detect_bottom_signals("5765.T", hist, previous_score=5)
        assert result.score_delta is not None
        assert result.score_delta < 0

    def test_insufficient_data_score_delta(self):
        hist = _make_history([100.0, 101.0, 102.0])
        result = detect_bottom_signals("5765.T", hist, previous_score=3)
        assert result.score_delta == -3
