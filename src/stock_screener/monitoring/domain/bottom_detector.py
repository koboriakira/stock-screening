from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from stock_screener.monitoring.domain.technical_indicators import (
    calc_bollinger_bands,
    calc_macd,
    calc_rsi,
    calc_volume_ratio,
)

RSI_OVERSOLD = 30
RSI_PERIOD = 14
BB_PERIOD = 20
BB_STD = 2
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
VOLUME_PERIOD = 5
VOLUME_THRESHOLD = 1.5
MA_PERIOD = 25
MIN_DATA_POINTS = 30


@dataclass(frozen=True)
class BottomSignal:
    """底打ちシグナルの検出結果。"""

    ticker: str
    score: int
    max_score: int
    level: str | None
    rsi_signal: bool
    bb_signal: bool
    macd_signal: bool
    volume_confirmed: bool
    ma_crossover: bool
    details: dict = field(default_factory=dict)


def _determine_level(score: int, volume_confirmed: bool) -> str | None:
    if score >= 3 and volume_confirmed:
        return "buy_candidate"
    if score >= 2 and volume_confirmed:
        return "attention"
    return None


def detect_bottom_signals(ticker: str, hist: pd.DataFrame) -> BottomSignal:
    """株価データから底打ちシグナルを検出する。

    Args:
        ticker: 銘柄コード
        hist: yfinance 形式の DataFrame (Close, Volume カラム必須)

    Returns:
        BottomSignal
    """
    if len(hist) < MIN_DATA_POINTS:
        return BottomSignal(
            ticker=ticker,
            score=0,
            max_score=5,
            level=None,
            rsi_signal=False,
            bb_signal=False,
            macd_signal=False,
            volume_confirmed=False,
            ma_crossover=False,
            details={},
        )

    close = hist["Close"]
    volume = hist["Volume"]

    # 1. RSI: oversold (<=30) から回復 (>30)
    rsi = calc_rsi(close, period=RSI_PERIOD)
    current_rsi = float(rsi.iloc[-1]) if not rsi.isna().iloc[-1] else 50.0
    prev_rsi = float(rsi.iloc[-2]) if len(rsi) > 1 and not rsi.isna().iloc[-2] else 50.0
    rsi_signal = prev_rsi <= RSI_OVERSOLD < current_rsi or current_rsi <= RSI_OVERSOLD

    # 2. BB: 下限バンド割れ -> バンド内に戻る
    upper, _middle, lower = calc_bollinger_bands(close, period=BB_PERIOD, num_std=BB_STD)
    current_close = float(close.iloc[-1])
    prev_close = float(close.iloc[-2]) if len(close) > 1 else current_close
    current_lower = float(lower.iloc[-1]) if not lower.isna().iloc[-1] else 0.0
    prev_lower = float(lower.iloc[-2]) if len(lower) > 1 and not lower.isna().iloc[-2] else 0.0
    bb_signal = prev_close <= prev_lower and current_close > current_lower
    band_width = float(upper.iloc[-1]) - current_lower
    bb_position = (current_close - current_lower) / band_width if band_width > 0 else 0.0

    # 3. MACD: signal line をゴールデンクロス
    _macd_line, _signal_line, histogram = calc_macd(close, fast=MACD_FAST, slow=MACD_SLOW, signal=MACD_SIGNAL)
    current_hist = float(histogram.iloc[-1]) if not histogram.isna().iloc[-1] else 0.0
    prev_hist = float(histogram.iloc[-2]) if len(histogram) > 1 and not histogram.isna().iloc[-2] else 0.0
    macd_signal_flag = prev_hist < 0 and current_hist >= 0

    # 4. 出来高: 5日平均の1.5倍以上
    vol_ratio = calc_volume_ratio(volume, period=VOLUME_PERIOD)
    volume_confirmed = vol_ratio >= VOLUME_THRESHOLD

    # 5. 25MA 上抜け
    if len(close) >= MA_PERIOD:
        ma = close.rolling(window=MA_PERIOD).mean()
        current_ma = float(ma.iloc[-1]) if not ma.isna().iloc[-1] else current_close
        prev_ma = float(ma.iloc[-2]) if len(ma) > 1 and not ma.isna().iloc[-2] else current_close
        ma_crossover = prev_close <= prev_ma and current_close > current_ma
    else:
        ma_crossover = False

    score = sum([rsi_signal, bb_signal, macd_signal_flag, volume_confirmed, ma_crossover])
    level = _determine_level(score, volume_confirmed)

    return BottomSignal(
        ticker=ticker,
        score=score,
        max_score=5,
        level=level,
        rsi_signal=rsi_signal,
        bb_signal=bb_signal,
        macd_signal=macd_signal_flag,
        volume_confirmed=volume_confirmed,
        ma_crossover=ma_crossover,
        details={
            "rsi": round(current_rsi, 2),
            "bb_position": round(bb_position, 4),
            "macd_histogram": round(current_hist, 4),
            "volume_ratio": round(vol_ratio, 2),
        },
    )
