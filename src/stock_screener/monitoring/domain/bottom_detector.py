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
RSI_BOTTOM_WINDOW = 5
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
    score_delta: int | None = None


def _determine_level(score: int, volume_confirmed: bool) -> str | None:
    if score >= 3 and volume_confirmed:
        return "buy_candidate"
    if score >= 2 and volume_confirmed:
        return "attention"
    return None


def _check_rsi_soft_bottom(rsi: pd.Series) -> bool:
    """RSI が 30 を割らなくても、直近 5 日で底打ちして上昇中かを判定する。"""
    if len(rsi) < RSI_BOTTOM_WINDOW:
        return False
    recent = rsi.iloc[-RSI_BOTTOM_WINDOW:]
    recent_valid = recent.dropna()
    if len(recent_valid) < 3:
        return False
    min_idx = recent_valid.to_numpy().argmin()
    # 最小値が先頭でも末尾でもない(底がある)、かつ現在値が最小値より高い
    if min_idx == 0 or min_idx == len(recent_valid) - 1:
        return False
    current_rsi = float(recent_valid.iloc[-1])
    min_rsi = float(recent_valid.iloc[min_idx])
    return current_rsi > min_rsi


def detect_bottom_signals(
    ticker: str,
    hist: pd.DataFrame,
    volume_threshold: float = VOLUME_THRESHOLD,
    previous_score: int | None = None,
) -> BottomSignal:
    """株価データから底打ちシグナルを検出する。

    Args:
        ticker: 銘柄コード
        hist: yfinance 形式の DataFrame (Close, Volume カラム必須)
        volume_threshold: 出来高確認の閾値(5日平均比)
        previous_score: 前回スコア(スコアデルタ計算用)

    Returns:
        BottomSignal
    """
    if len(hist) < MIN_DATA_POINTS:
        score = 0
        score_delta = score - previous_score if previous_score is not None else None
        return BottomSignal(
            ticker=ticker,
            score=score,
            max_score=5,
            level=None,
            rsi_signal=False,
            bb_signal=False,
            macd_signal=False,
            volume_confirmed=False,
            ma_crossover=False,
            details={},
            score_delta=score_delta,
        )

    close = hist["Close"]
    volume = hist["Volume"]

    # 1. RSI: oversold (<=30) から回復 (>30) OR ソフト底打ち検出
    rsi = calc_rsi(close, period=RSI_PERIOD)
    current_rsi = float(rsi.iloc[-1]) if not rsi.isna().iloc[-1] else 50.0
    prev_rsi = float(rsi.iloc[-2]) if len(rsi) > 1 and not rsi.isna().iloc[-2] else 50.0
    rsi_classic = prev_rsi <= RSI_OVERSOLD < current_rsi or current_rsi <= RSI_OVERSOLD
    rsi_soft = _check_rsi_soft_bottom(rsi)
    rsi_signal = rsi_classic or rsi_soft

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

    # 4. 出来高: 5日平均の threshold 倍以上
    vol_ratio = calc_volume_ratio(volume, period=VOLUME_PERIOD)
    volume_confirmed = vol_ratio >= volume_threshold

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
    score_delta = score - previous_score if previous_score is not None else None

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
        score_delta=score_delta,
    )
