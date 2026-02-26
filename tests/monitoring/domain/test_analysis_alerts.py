"""分析データに基づくアラート生成のテスト。"""

from datetime import date

from stock_screener.monitoring.domain.analysis import (
    AnalysisData,
    KeyDate,
    KeyDateRange,
    PriceLevel,
    Risk,
)
from stock_screener.monitoring.domain.analysis_alerts import generate_analysis_alerts


def _make_analysis() -> AnalysisData:
    return AnalysisData(
        ticker="4486.T",
        updated_at=date(2026, 2, 26),
        thesis="テスト用テーゼ",
        supports=[
            PriceLevel(price=650, label="200日移動平均"),
            PriceLevel(price=600, label="心理的節目"),
        ],
        resistances=[
            PriceLevel(price=700, label="短期移動平均"),
            PriceLevel(price=785, label="52週高値"),
        ],
        key_dates=[
            KeyDate(date=date(2026, 3, 31), event="配当権利確定", severity="medium"),
            KeyDateRange(
                start=date(2026, 4, 1),
                end=date(2026, 5, 31),
                event="信用期日到来集中",
                severity="high",
            ),
        ],
        catalysts=[],
        risks=[
            Risk(
                id="R1",
                description="信用期日到来の売り圧力",
                timing="4-5月",
                impact="high",
                probability="high",
            ),
        ],
    )


class TestGenerateAnalysisAlerts:
    def test_support_approach_alert(self):
        """サポートライン接近時にアラートが生成される"""
        analysis = _make_analysis()
        # 665 は 650 の +2.3% → 3% 以内
        alerts = generate_analysis_alerts(analysis, current_price=665, today=date(2026, 2, 26))
        support_alerts = [a for a in alerts if a["type"] == "support_approach"]
        assert len(support_alerts) == 1
        assert support_alerts[0]["level"]["price"] == 650

    def test_no_support_alert_when_far(self):
        """サポートから遠い場合はアラートなし"""
        analysis = _make_analysis()
        alerts = generate_analysis_alerts(analysis, current_price=690, today=date(2026, 2, 26))
        support_alerts = [a for a in alerts if a["type"] == "support_approach"]
        assert len(support_alerts) == 0

    def test_resistance_approach_alert(self):
        """レジスタンスライン接近時にアラートが生成される"""
        analysis = _make_analysis()
        # 690 は 700 の -1.4% → 3% 以内
        alerts = generate_analysis_alerts(analysis, current_price=690, today=date(2026, 2, 26))
        resistance_alerts = [a for a in alerts if a["type"] == "resistance_approach"]
        assert len(resistance_alerts) == 1
        assert resistance_alerts[0]["level"]["price"] == 700

    def test_key_date_alert(self):
        """重要日が 5日以内の場合にアラートが生成される"""
        analysis = _make_analysis()
        alerts = generate_analysis_alerts(analysis, current_price=675, today=date(2026, 3, 28))
        date_alerts = [a for a in alerts if a["type"] == "key_date_approaching"]
        assert len(date_alerts) >= 1
        events = {a["event"] for a in date_alerts}
        assert "配当権利確定" in events

    def test_in_date_range_alert(self):
        """重要期間中の場合にアラートが生成される"""
        analysis = _make_analysis()
        alerts = generate_analysis_alerts(analysis, current_price=675, today=date(2026, 4, 15))
        date_alerts = [a for a in alerts if a["type"] == "key_date_approaching"]
        events = {a["event"] for a in date_alerts}
        assert "信用期日到来集中" in events

    def test_no_alerts_when_normal(self):
        """異常なし（サポート/レジスタンス遠い、重要日遠い）"""
        analysis = _make_analysis()
        alerts = generate_analysis_alerts(analysis, current_price=675, today=date(2026, 2, 26))
        assert len(alerts) == 0

    def test_empty_analysis_no_alerts(self):
        """空の分析データではアラートなし"""
        analysis = AnalysisData(
            ticker="9999.T",
            updated_at=date(2026, 2, 26),
            thesis="空",
        )
        alerts = generate_analysis_alerts(analysis, current_price=1000, today=date(2026, 2, 26))
        assert len(alerts) == 0
