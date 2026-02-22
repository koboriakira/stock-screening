from __future__ import annotations

from datetime import date

import numpy as np

from stock_screener.timing.domain.calendar_schedule import CalendarData
from stock_screener.timing.domain.config import (
    DIVIDEND_RECORD_MAX_DAYS,
    DIVIDEND_RECORD_MIN_DAYS,
    EARNINGS_BLACKOUT_DAYS,
    MA_TOLERANCE,
    MIN_AVG_VOLUME_5D,
    POST_EARNINGS_MAX_DAYS,
    POST_EARNINGS_MIN_DAYS,
    SIGNAL_THRESHOLD,
)
from stock_screener.timing.domain.portfolio import Portfolio
from stock_screener.timing.domain.sizing import check_sizing


def _business_days_between(start: date, end: date) -> int:
    """start から end までの営業日数を計算する(簡易版: 土日のみ除外)。"""
    return int(np.busday_count(start.isoformat(), end.isoformat()))


def check_blockers(
    ticker: str,
    market_data: dict,
    calendar: CalendarData,
    today: date,
) -> tuple[str, list[dict]]:
    """ブロッカー判定 B1-B3 を実行する。

    Returns:
        ("pass", details) or ("wait", details)
    """
    details: list[dict] = []

    # B1: 決算直前回避
    ticker_cal = calendar.get(ticker)
    if ticker_cal is not None:
        latest = ticker_cal.latest_earnings()
        if latest is not None and latest.next_date is not None:
            next_date = date.fromisoformat(latest.next_date)
            bdays = _business_days_between(today, next_date)
            threshold = EARNINGS_BLACKOUT_DAYS
            if not latest.is_confirmed:
                threshold += 3
            if bdays <= threshold:
                details.append({
                    "id": "B1",
                    "result": "FAIL",
                    "message": f"決算{bdays}営業日前 (閾値={threshold})",
                })
            else:
                details.append({
                    "id": "B1",
                    "result": "PASS",
                    "message": f"決算{bdays}営業日前 (閾値={threshold})",
                })
        else:
            details.append({"id": "B1", "result": "PASS", "message": "次回決算日未設定"})
    else:
        details.append({"id": "B1", "result": "PASS", "message": "カレンダー未登録"})

    # B2: ストップ高/安
    if market_data.get("is_stop_limit", False):
        details.append({"id": "B2", "result": "FAIL", "message": "ストップ高/安検出"})
    else:
        details.append({"id": "B2", "result": "PASS", "message": "ストップ高/安なし"})

    # B3: 出来高枯渇
    avg_vol = market_data.get("avg_volume_5d", 0)
    if avg_vol < MIN_AVG_VOLUME_5D:
        details.append({
            "id": "B3",
            "result": "FAIL",
            "message": f"5日平均出来高={avg_vol:.0f} (最低={MIN_AVG_VOLUME_5D})",
        })
    else:
        details.append({
            "id": "B3",
            "result": "PASS",
            "message": f"5日平均出来高={avg_vol:.0f}",
        })

    overall = "wait" if any(d["result"] == "FAIL" for d in details) else "pass"
    return (overall, details)


def calc_signal_score(
    ticker: str,
    market_data: dict,
    calendar: CalendarData,
    today: date,
) -> tuple[int, list[dict]]:
    """シグナルスコア S1-S5 を計算する。

    Returns:
        (score, details)
    """
    details: list[dict] = []
    total_score = 0

    # S1: 株価位置(25MA)
    current_price = market_data["current_price"]
    ma25 = market_data.get("ma25")
    if ma25 is not None and current_price <= ma25 * MA_TOLERANCE:
        ma_limit = ma25 * MA_TOLERANCE
        details.append({"id": "S1", "score": 1, "message": f"株価{current_price} <= {ma_limit:.0f}"})
        total_score += 1
    else:
        ma_msg = f"MA25*{MA_TOLERANCE}={ma25 * MA_TOLERANCE:.0f}" if ma25 else "MA25未算出"
        details.append({"id": "S1", "score": 0, "message": f"株価{current_price} > {ma_msg}"})

    # S2: 決算後初動
    ticker_cal = calendar.get(ticker)
    if ticker_cal is not None:
        latest = ticker_cal.latest_earnings()
        if latest is not None and latest.announced_date is not None:
            ann_date = date.fromisoformat(latest.announced_date)
            elapsed = _business_days_between(ann_date, today)
            if POST_EARNINGS_MIN_DAYS <= elapsed <= POST_EARNINGS_MAX_DAYS:
                details.append({"id": "S2", "score": 1, "message": f"決算後{elapsed}営業日"})
                total_score += 1
            else:
                details.append({"id": "S2", "score": 0, "message": f"決算後{elapsed}営業日 (範囲外)"})
        else:
            details.append({"id": "S2", "score": 0, "message": "決算発表日未設定"})
    else:
        details.append({"id": "S2", "score": 0, "message": "カレンダー未登録"})

    # S3: 信用倍率改善 (スケルトン)
    details.append({"id": "S3", "score": 0, "message": "MANUAL_REQUIRED(calendar.jsonにshintaku_ratioを手動登録)"})

    # S4: 上方修正後 (スケルトン)
    details.append({"id": "S4", "score": 0, "message": "MANUAL_REQUIRED(EDINET連携未実装)"})

    # S5: 配当権利付き
    if ticker_cal is not None and ticker_cal.dividend.record_date is not None:
        rec_date = date.fromisoformat(ticker_cal.dividend.record_date)
        days_to_record = (rec_date - today).days
        if DIVIDEND_RECORD_MIN_DAYS <= days_to_record <= DIVIDEND_RECORD_MAX_DAYS:
            details.append({"id": "S5", "score": 1, "message": f"権利確定{days_to_record}日前"})
            total_score += 1
        else:
            details.append({"id": "S5", "score": 0, "message": f"権利確定{days_to_record}日前 (範囲外)"})
    else:
        details.append({"id": "S5", "score": 0, "message": "権利確定日未設定"})

    return (total_score, details)


def evaluate_entry(
    ticker: str,
    market_data: dict,
    portfolio: Portfolio,
    calendar: CalendarData,
    today: date,
) -> dict:
    """エントリー判定を統合する。

    Returns:
        {
            "ticker": str,
            "sizing_result": "pass|skip",
            "sizing_message": str,
            "blocker_result": "pass|wait",
            "blocker_details": list,
            "signal_score": int,
            "signal_details": list,
            "verdict": "buy|wait|skip",
            "current_price": float,
        }
    """
    current_price = market_data["current_price"]

    sizing_result, sizing_message = check_sizing(ticker, current_price, portfolio)
    blocker_result, blocker_details = check_blockers(ticker, market_data, calendar, today)
    signal_score, signal_details = calc_signal_score(ticker, market_data, calendar, today)

    if sizing_result == "skip":
        verdict = "skip"
    elif blocker_result == "wait":
        verdict = "wait"
    elif signal_score >= SIGNAL_THRESHOLD:
        verdict = "buy"
    else:
        verdict = "wait"

    return {
        "ticker": ticker,
        "sizing_result": sizing_result,
        "sizing_message": sizing_message,
        "blocker_result": blocker_result,
        "blocker_details": blocker_details,
        "signal_score": signal_score,
        "signal_details": signal_details,
        "verdict": verdict,
        "current_price": current_price,
    }
