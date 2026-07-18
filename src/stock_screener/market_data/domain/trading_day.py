from __future__ import annotations

from datetime import date, time, timedelta

import pandas_market_calendars as mcal


def is_trading_day(target: date) -> bool:
    """JPX(東京証券取引所)の営業日かどうかを判定する。"""
    jpx = mcal.get_calendar("JPX")
    schedule = jpx.schedule(start_date=target.isoformat(), end_date=target.isoformat())
    return len(schedule) > 0


def n_trading_days_after(target: date, n: int) -> date:
    """target から n 営業日後の日付を返す(target 自体は含めない、n>=1)。"""
    jpx = mcal.get_calendar("JPX")
    buffer_days = n * 3 + 16
    end_date = target + timedelta(days=buffer_days)
    schedule = jpx.schedule(start_date=target.isoformat(), end_date=end_date.isoformat())
    trading_days = [ts.date() for ts in schedule.index if ts.date() > target]
    return trading_days[n - 1]


def next_trading_day(target: date) -> date:
    """target の翌営業日を返す(target 自体は含めない)。"""
    return n_trading_days_after(target, 1)


def market_open_close(target: date) -> tuple[time, time] | None:
    """target の寄付・引け時刻を JST の time で返す。非営業日は None。"""
    jpx = mcal.get_calendar("JPX")
    schedule = jpx.schedule(start_date=target.isoformat(), end_date=target.isoformat())
    if schedule.empty:
        return None
    row = schedule.iloc[0]
    open_time = row["market_open"].tz_convert("Asia/Tokyo").time()
    close_time = row["market_close"].tz_convert("Asia/Tokyo").time()
    return open_time, close_time
