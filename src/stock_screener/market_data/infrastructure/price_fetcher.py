from __future__ import annotations

import pandas as pd
import yfinance as yf

from stock_screener.shared.retry import retry_on_rate_limit


def fetch_history(symbol: str, period: str, interval: str = "1d") -> pd.DataFrame:
    """yfinance から価格履歴を取得する。

    キャッシュは行わない。リトライ後も取得できない場合は例外を伝播させる。
    """
    return retry_on_rate_limit(
        lambda: yf.Ticker(symbol).history(period=period, interval=interval),
        max_retries=2,
        base_delay=1.0,
    )
