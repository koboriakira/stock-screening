from __future__ import annotations

import dataclasses

import pandas as pd

from stock_screener.signals.domain.bottom_detector import detect_bottom_signals


def compute_signals(ticker: str, hist: pd.DataFrame, volume_threshold: float = 1.5) -> dict:
    """底打ちシグナルを計算し、JSON items 用の dict に変換する。"""
    signal = detect_bottom_signals(ticker, hist, volume_threshold=volume_threshold)
    return dataclasses.asdict(signal)
