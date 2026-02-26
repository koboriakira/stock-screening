from datetime import date

from stock_screener.monitoring.domain.analysis import (
    AnalysisData,
    Catalyst,
    KeyDate,
    KeyDateRange,
    PriceLevel,
    Risk,
)


class TestAnalysisDataSerialization:
    def _make_analysis(self) -> AnalysisData:
        return AnalysisData(
            ticker="4486.T",
            updated_at=date(2026, 2, 26),
            thesis="業績◎・需給×の小型グロース",
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
                KeyDate(date=date(2026, 5, 15), event="Q1決算発表", severity="high"),
            ],
            catalysts=[
                Catalyst(
                    id="C1", description="Q1決算で高進捗率", timing="5月中旬", impact="high", probability="medium",
                ),
            ],
            risks=[
                Risk(id="R1", description="信用期日到来の売り圧力", timing="4〜5月", impact="high", probability="high"),
            ],
        )

    def test_roundtrip(self):
        """to_dict → from_dict で元のデータが復元される"""
        original = self._make_analysis()
        restored = AnalysisData.from_dict(original.to_dict())
        assert restored.ticker == original.ticker
        assert restored.updated_at == original.updated_at
        assert restored.thesis == original.thesis
        assert len(restored.supports) == 2
        assert len(restored.resistances) == 2
        assert restored.supports[0].price == 650
        assert restored.resistances[1].label == "52週高値"
        assert len(restored.key_dates) == 3
        assert len(restored.catalysts) == 1
        assert len(restored.risks) == 1

    def test_key_date_types_preserved(self):
        """KeyDate と KeyDateRange が正しく復元される"""
        original = self._make_analysis()
        d = original.to_dict()
        restored = AnalysisData.from_dict(d)
        assert isinstance(restored.key_dates[0], KeyDate)
        assert isinstance(restored.key_dates[1], KeyDateRange)
        assert restored.key_dates[1].start == date(2026, 4, 1)
        assert restored.key_dates[1].end == date(2026, 5, 31)


class TestAnalysisAlerts:
    def _make_analysis(self) -> AnalysisData:
        return AnalysisData(
            ticker="4486.T",
            updated_at=date(2026, 2, 26),
            thesis="テスト",
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
            risks=[],
        )

    def test_nearest_support_when_price_above_all(self):
        """現在値がすべてのサポートより上 → 最も近い(高い)サポートを返す"""
        a = self._make_analysis()
        level = a.nearest_support(675)
        assert level is not None
        assert level.price == 650

    def test_nearest_support_when_price_below_all(self):
        """現在値がすべてのサポートより下 → None"""
        a = self._make_analysis()
        assert a.nearest_support(500) is None

    def test_nearest_resistance_when_price_below_all(self):
        """現在値がすべてのレジスタンスより下 → 最も近い(低い)レジスタンスを返す"""
        a = self._make_analysis()
        level = a.nearest_resistance(675)
        assert level is not None
        assert level.price == 700

    def test_nearest_resistance_when_price_above_all(self):
        """現在値がすべてのレジスタンスより上 → None"""
        a = self._make_analysis()
        assert a.nearest_resistance(800) is None

    def test_approaching_support(self):
        """サポートの +3% 以内 → approaching"""
        a = self._make_analysis()
        # 650 * 1.03 = 669.5 → 669 は +3% 以内
        assert a.is_approaching_support(669, threshold_pct=0.03)
        # 680 は 650 から +4.6% → 超えている
        assert not a.is_approaching_support(680, threshold_pct=0.03)

    def test_approaching_resistance(self):
        """レジスタンスの -3% 以内 → approaching"""
        a = self._make_analysis()
        # 700 * 0.97 = 679 → 690 は -3% 以内
        assert a.is_approaching_resistance(690, threshold_pct=0.03)
        # 650 は 700 から -7.1% → 超えている
        assert not a.is_approaching_resistance(650, threshold_pct=0.03)

    def test_active_key_dates_point(self):
        """特定の日付の key_date が 5日以内にある"""
        a = self._make_analysis()
        active = a.upcoming_key_dates(today=date(2026, 3, 28), lookahead_days=5)
        # 3/31(配当権利) + 4/1-5/31(信用期日) の両方がヒット
        assert len(active) == 2
        events = {kd.event for kd in active}
        assert "配当権利確定" in events
        assert "信用期日到来集中" in events

    def test_active_key_dates_range(self):
        """date_range の期間内にいる"""
        a = self._make_analysis()
        active = a.upcoming_key_dates(today=date(2026, 4, 15), lookahead_days=5)
        assert any(kd.event == "信用期日到来集中" for kd in active)

    def test_no_active_key_dates(self):
        """該当する key_date がない"""
        a = self._make_analysis()
        active = a.upcoming_key_dates(today=date(2026, 1, 1), lookahead_days=5)
        assert len(active) == 0
