from datetime import date

from stock_screener.monitoring.domain.analysis import (
    AnalysisData,
    Catalyst,
    KeyDate,
    KeyDateRange,
    PriceLevel,
    Risk,
)
from stock_screener.monitoring.infrastructure.analysis_repository import AnalysisRepository


def _make_analysis() -> AnalysisData:
    return AnalysisData(
        ticker="4486.T",
        updated_at=date(2026, 2, 26),
        thesis="業績◎・需給×の小型グロース",
        supports=[PriceLevel(price=650, label="200日移動平均")],
        resistances=[PriceLevel(price=700, label="短期移動平均")],
        key_dates=[
            KeyDate(date=date(2026, 3, 31), event="配当権利確定", severity="medium"),
            KeyDateRange(start=date(2026, 4, 1), end=date(2026, 5, 31), event="信用期日", severity="high"),
        ],
        catalysts=[Catalyst(id="C1", description="Q1好決算", timing="5月", impact="high", probability="medium")],
        risks=[Risk(id="R1", description="信用売り圧力", timing="4月", impact="high", probability="high")],
    )


class TestAnalysisRepository:
    def test_save_and_load_json(self, tmp_path):
        """JSON の保存・読み込みが正しく動作する"""
        repo = AnalysisRepository(base_dir=tmp_path)
        analysis = _make_analysis()
        repo.save(analysis)

        loaded = repo.load("4486.T")
        assert loaded is not None
        assert loaded.ticker == "4486.T"
        assert loaded.thesis == "業績◎・需給×の小型グロース"
        assert len(loaded.supports) == 1
        assert len(loaded.key_dates) == 2

    def test_save_and_load_markdown(self, tmp_path):
        """Markdown の保存・読み込みが正しく動作する"""
        repo = AnalysisRepository(base_dir=tmp_path)
        md_text = "# 4486.T の分析\n\nテスト内容"
        repo.save_markdown("4486.T", md_text)

        loaded = repo.load_markdown("4486.T")
        assert loaded == md_text

    def test_load_nonexistent_returns_none(self, tmp_path):
        """存在しないティッカーの読み込みは None を返す"""
        repo = AnalysisRepository(base_dir=tmp_path)
        assert repo.load("9999.T") is None
        assert repo.load_markdown("9999.T") is None

    def test_list_tickers(self, tmp_path):
        """保存済みティッカーの一覧を返す"""
        repo = AnalysisRepository(base_dir=tmp_path)
        repo.save(_make_analysis())

        a2 = AnalysisData(
            ticker="5599.T",
            updated_at=date(2026, 2, 26),
            thesis="テスト",
        )
        repo.save(a2)

        tickers = repo.list_tickers()
        assert sorted(tickers) == ["4486.T", "5599.T"]
