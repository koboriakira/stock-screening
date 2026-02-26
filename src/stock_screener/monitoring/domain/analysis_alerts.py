"""分析データに基づくアラート生成。"""

from __future__ import annotations

from datetime import date

from stock_screener.monitoring.domain.analysis import AnalysisData, KeyDate, KeyDateRange

SUPPORT_THRESHOLD_PCT = 0.03
RESISTANCE_THRESHOLD_PCT = 0.03
KEY_DATE_LOOKAHEAD_DAYS = 5


def generate_analysis_alerts(
    analysis: AnalysisData,
    current_price: float,
    today: date,
) -> list[dict]:
    """分析データと現在の状況からアラートのリストを生成する。

    Returns:
        list[dict] - 各アラートは以下の形式:
            {"type": "support_approach", "level": {"price": 650, "label": "..."}, "ticker": "4486.T"}
            {"type": "resistance_approach", "level": {"price": 700, "label": "..."}, "ticker": "4486.T"}
            {"type": "key_date_approaching", "event": "...", "severity": "...", "ticker": "4486.T"}
    """
    alerts: list[dict] = []

    # サポートライン接近
    if analysis.is_approaching_support(current_price, threshold_pct=SUPPORT_THRESHOLD_PCT):
        support = analysis.nearest_support(current_price)
        if support is not None:
            alerts.append({
                "type": "support_approach",
                "ticker": analysis.ticker,
                "level": {"price": support.price, "label": support.label},
                "current_price": current_price,
            })

    # レジスタンスライン接近
    if analysis.is_approaching_resistance(current_price, threshold_pct=RESISTANCE_THRESHOLD_PCT):
        resistance = analysis.nearest_resistance(current_price)
        if resistance is not None:
            alerts.append({
                "type": "resistance_approach",
                "ticker": analysis.ticker,
                "level": {"price": resistance.price, "label": resistance.label},
                "current_price": current_price,
            })

    # 重要日接近 / 期間中
    upcoming = analysis.upcoming_key_dates(today=today, lookahead_days=KEY_DATE_LOOKAHEAD_DAYS)
    for kd in upcoming:
        alert: dict = {
            "type": "key_date_approaching",
            "ticker": analysis.ticker,
            "event": kd.event,
            "severity": kd.severity,
        }
        if isinstance(kd, KeyDateRange):
            alert["start"] = kd.start.isoformat()
            alert["end"] = kd.end.isoformat()
            alert["in_range"] = kd.start <= today <= kd.end
        elif isinstance(kd, KeyDate):
            alert["date"] = kd.date.isoformat()
            alert["days_until"] = (kd.date - today).days
        alerts.append(alert)

    return alerts


def format_analysis_alert_message(alert: dict) -> str:
    """アラートを Slack 通知用テキストにフォーマットする。"""
    ticker = alert["ticker"]
    alert_type = alert["type"]

    if alert_type == "support_approach":
        level = alert["level"]
        return (
            f"[サポート接近] {ticker}\n"
            f"現在値: {alert['current_price']:,.0f}\n"
            f"サポート: {level['price']:,.0f} ({level['label']})"
        )

    if alert_type == "resistance_approach":
        level = alert["level"]
        return (
            f"[レジスタンス接近] {ticker}\n"
            f"現在値: {alert['current_price']:,.0f}\n"
            f"レジスタンス: {level['price']:,.0f} ({level['label']})"
        )

    if alert_type == "key_date_approaching":
        severity_mark = {"high": "!!!", "medium": "!!", "low": "!"}.get(alert["severity"], "")
        if alert.get("in_range"):
            return f"[重要期間中{severity_mark}] {ticker}\n{alert['event']}"
        days = alert.get("days_until", "?")
        return f"[重要日接近{severity_mark}] {ticker}\n{alert['event']} ({days}日後)"

    return f"[分析アラート] {ticker}: {alert_type}"
