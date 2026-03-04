from __future__ import annotations

from datetime import date

from stock_screener.monitoring.domain.bottom_detector import BottomSignal


def format_daily_summary(
    monitor_results: list[dict],
    watchlist_results: list[dict],
    today: date,
    analysis_alerts: list[dict],
) -> str:
    """日次モニタリングのサマリーテキストを生成する。"""
    lines: list[str] = [f"[日次モニタリング {today.strftime('%m/%d')}]"]

    lines.append("■ 保有銘柄")
    if monitor_results:
        for r in monitor_results:
            lines.extend(_format_holding(r, today))
    else:
        lines.append("・対象なし")

    lines.append("■ ウォッチリスト")
    if watchlist_results:
        for r in watchlist_results:
            lines.extend(_format_watchlist_entry(r))
    else:
        lines.append("・対象なし")

    if analysis_alerts:
        lines.append("■ 分析アラート")
        lines.extend(_format_analysis_alert(alert) for alert in analysis_alerts)

    return "\n".join(lines)


def _format_holding(r: dict, today: date) -> list[str]:
    ticker = r["ticker"]
    name = r.get("name", "")
    action = r["action"]
    current = r["current_price"]
    entry = r.get("entry_price", 0)
    pnl_pct = r.get("unrealized_pnl_pct", 0)
    days_held = r.get("days_held", 0)
    max_holding = r.get("max_holding_date", "")
    stop_loss = r.get("stop_loss", 0)
    target_price = r.get("target_price", 0)

    days_remaining = 0
    if max_holding:
        max_date = date.fromisoformat(max_holding) if isinstance(max_holding, str) else max_holding
        days_remaining = (max_date - today).days

    stop_dist = (stop_loss - current) / current * 100 if current else 0
    target_dist = (target_price - current) / current * 100 if current else 0

    return [
        f"・{ticker} {name}: {action}",
        f"  {current:,.0f}円(取得{entry:,.0f}円) {pnl_pct * 100:+.1f}% | 保有{days_held}日/残{days_remaining}日",
        f"  損切りまで{stop_dist:+.1f}% 利確まで{target_dist:+.1f}%",
    ]


def _format_watchlist_entry(r: dict) -> list[str]:
    ticker = r["ticker"]
    name = r.get("name", "")
    signal: BottomSignal = r["signal"]
    current_price = r.get("current_price")
    price_change_pct = r.get("price_change_pct")
    reasons = r.get("score_change_reasons", [])

    price_str = f"{current_price:,.0f}" if current_price is not None else "-"
    pct_str = f"{price_change_pct * 100:+.1f}%" if price_change_pct is not None else "-"
    if signal.score_delta is None:
        delta_str = "-"
    elif signal.score_delta >= 0:
        delta_str = f"+{signal.score_delta}"
    else:
        delta_str = str(signal.score_delta)

    header = f"・{ticker} {name} {price_str}円({pct_str}) スコア{signal.score}/{signal.max_score}({delta_str})"

    sig_line = (
        f"  RSI:{_mark(signal.rsi_signal)} "
        f"BB:{_mark(signal.bb_signal)} "
        f"MACD:{_mark(signal.macd_signal)} "
        f"出来高:{_mark(signal.volume_confirmed)} "
        f"MA:{_mark(signal.ma_crossover)}"
    )
    if reasons:
        sig_line += f" ← {'↑' if any('点灯' in r for r in reasons) else '↓'}{''.join(reasons)}"

    details = signal.details
    rsi_val = details.get("rsi", "-")
    vol_ratio = details.get("volume_ratio", "-")
    detail_line = f"  RSI:{rsi_val} 出来高比:{vol_ratio}"

    return [header, sig_line, detail_line]


def _format_analysis_alert(alert: dict) -> str:
    alert_type = alert["type"]
    ticker = alert["ticker"]
    if alert_type == "support_approach":
        lvl = alert["level"]
        return f"  [サポート接近] {ticker}: {lvl['price']:,.0f} ({lvl['label']})"
    if alert_type == "resistance_approach":
        lvl = alert["level"]
        return f"  [レジスタンス接近] {ticker}: {lvl['price']:,.0f} ({lvl['label']})"
    if alert_type == "key_date_approaching":
        sev = {"high": "!!!", "medium": "!!", "low": "!"}.get(alert.get("severity", ""), "")
        return f"  [重要日{sev}] {ticker}: {alert['event']}"
    return f"  [{alert_type}] {ticker}"


def _mark(value: bool) -> str:
    return "o" if value else "x"
