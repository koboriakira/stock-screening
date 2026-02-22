from __future__ import annotations

from datetime import date

import pandas_market_calendars as mcal


def is_trading_day(target: date) -> bool:
    """JPX(東京証券取引所)の営業日かどうかを判定する。"""
    jpx = mcal.get_calendar("JPX")
    schedule = jpx.schedule(start_date=target.isoformat(), end_date=target.isoformat())
    return len(schedule) > 0
