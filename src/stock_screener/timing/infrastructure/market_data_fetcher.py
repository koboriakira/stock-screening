from __future__ import annotations

import logging

import yfinance as yf

from stock_screener.timing.domain.config import MA_PERIOD

logger = logging.getLogger(__name__)


def fetch_market_data(ticker: str) -> dict | None:
    """yfinance からマーケットデータを取得する。

    Returns:
        {
            "current_price": float,
            "ma25": float,
            "avg_volume_5d": float,
            "is_stop_limit": bool,
        }
        取得失敗時は None。
    """
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="3mo")
        if hist.empty:
            logger.warning("%s: 株価データ取得失敗(空)", ticker)
            return None

        current_price = float(hist["Close"].iloc[-1])

        # 25日移動平均
        if len(hist) >= MA_PERIOD:
            ma25 = float(hist["Close"].rolling(window=MA_PERIOD).mean().iloc[-1])
        else:
            ma25 = float(hist["Close"].mean())

        # 5日平均出来高
        avg_volume_5d = float(hist["Volume"].tail(5).mean())

        # ストップ高/安の推定
        latest = hist.iloc[-1]
        high = float(latest["High"])
        low = float(latest["Low"])
        close = float(latest["Close"])
        is_stop_limit = (
            low > 0
            and (high - low) / low < 0.001
            and close in {high, low}
        )

        return {
            "current_price": current_price,
            "ma25": ma25,
            "avg_volume_5d": avg_volume_5d,
            "is_stop_limit": is_stop_limit,
        }
    except Exception:
        logger.exception("%s: マーケットデータ取得エラー", ticker)
        return None
