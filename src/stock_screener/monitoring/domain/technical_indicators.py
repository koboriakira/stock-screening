from __future__ import annotations

import pandas as pd


def calc_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """RSI (Relative Strength Index) を計算する。"""
    delta = prices.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)

    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def calc_bollinger_bands(
    prices: pd.Series,
    period: int = 20,
    num_std: int = 2,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """ボリンジャーバンドを計算する。

    Returns:
        (upper, middle, lower)
    """
    middle = prices.rolling(window=period).mean()
    std = prices.rolling(window=period).std()
    upper = middle + num_std * std
    lower = middle - num_std * std
    return upper, middle, lower


def calc_macd(
    prices: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """MACD (Moving Average Convergence Divergence) を計算する。

    Returns:
        (macd_line, signal_line, histogram)
    """
    ema_fast = prices.ewm(span=fast, adjust=False).mean()
    ema_slow = prices.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def calc_volume_ratio(volumes: pd.Series, period: int = 5) -> float:
    """直近出来高の N 日平均に対する比率を計算する。"""
    if len(volumes) < period + 1:
        return 0.0
    avg = volumes.iloc[-(period + 1) : -1].mean()
    if avg == 0:
        return 0.0
    return float(volumes.iloc[-1] / avg)
