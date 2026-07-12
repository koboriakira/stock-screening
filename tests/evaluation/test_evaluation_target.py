from __future__ import annotations

from stock_screener.discovery.domain.candidate import Candidate
from stock_screener.discovery.domain.scoring import ScoreResult
from stock_screener.evaluation.domain.evaluation_target import EvaluationTarget
from stock_screener.market_data.domain.financial_snapshot import FinancialSnapshot
from stock_screener.market_data.domain.security import Security
from stock_screener.shared.types import Ticker


def _make_candidate() -> Candidate:
    return Candidate(
        security=Security(
            ticker=Ticker("7203"),
            company_name="トヨタ自動車",
            sector="輸送用機器",
            financial_snapshot=FinancialSnapshot(per=10.5, pbr=1.2, net_cash_ratio=0.25),
        ),
        score=ScoreResult(value=60.0, quality=50.0, momentum=40.0, total=51.0),
        rank=3,
    )


class TestEvaluationTarget:
    def test_from_candidate(self):
        candidate = _make_candidate()
        target = EvaluationTarget.from_candidate(candidate)
        assert target.ticker == Ticker("7203")
        assert target.company_name == "トヨタ自動車"
        assert target.sector == "輸送用機器"
        assert target.discovery_rank == 3
        assert target.score_total == 51.0

    def test_from_candidate_preserves_snapshot(self):
        candidate = _make_candidate()
        target = EvaluationTarget.from_candidate(candidate)
        assert target.financial_snapshot.per == 10.5
        assert target.financial_snapshot.pbr == 1.2
        assert target.financial_snapshot.net_cash_ratio == 0.25

    def test_from_csv_row(self):
        row = {
            "ticker": "7203",
            "company_name": "トヨタ自動車",
            "sector": "輸送用機器",
            "rank": "3",
            "total_score": "51.0",
            "per": "10.5",
            "pbr": "1.2",
            "roe": "",
            "market_cap": "30000000000",
        }
        target = EvaluationTarget.from_csv_row(row)
        assert target.ticker == Ticker("7203")
        assert target.company_name == "トヨタ自動車"
        assert target.discovery_rank == 3
        assert target.score_total == 51.0
        assert target.financial_snapshot.per == 10.5
        assert target.financial_snapshot.roe is None

    def test_from_csv_row_empty_values(self):
        row = {
            "ticker": "6861",
            "company_name": "キーエンス",
            "sector": "電気機器",
            "rank": "1",
            "total_score": "85.0",
            "per": "",
            "pbr": "",
            "roe": "",
            "market_cap": "",
        }
        target = EvaluationTarget.from_csv_row(row)
        assert target.financial_snapshot.per is None
        assert target.financial_snapshot.pbr is None
        assert target.financial_snapshot.market_cap is None


class TestFromSnapshot:
    """from_snapshot が単銘柄指定(evaluateコマンドの positional ticker)向けに生成するテスト。"""

    def test_from_snapshot_minimal(self):
        snapshot = FinancialSnapshot(per=10.5, pbr=1.2, net_cash_ratio=0.25)
        target = EvaluationTarget.from_snapshot(ticker=Ticker("7203"), financial_snapshot=snapshot)
        assert target.ticker == Ticker("7203")
        assert target.financial_snapshot is snapshot
        assert target.discovery_rank is None
        assert target.score_total is None
        assert target.company_name is None
        assert target.sector == ""
        assert target.anomaly_flags == []

    def test_from_snapshot_with_company_name(self):
        snapshot = FinancialSnapshot(per=10.5)
        target = EvaluationTarget.from_snapshot(
            ticker=Ticker("7203"),
            financial_snapshot=snapshot,
            company_name="トヨタ自動車",
            sector="輸送用機器",
        )
        assert target.company_name == "トヨタ自動車"
        assert target.sector == "輸送用機器"


class TestFromCsvRowFullMapping:
    """from_csv_row がCSVの全フィールドを FinancialSnapshot にマッピングするテスト。"""

    def _make_full_row(self) -> dict[str, str]:
        return {
            "rank": "1",
            "ticker": "3916",
            "company_name": "DIT",
            "sector": "情報・通信業",
            "total_score": "84.5",
            "per": "7.4",
            "pbr": "0.8",
            "roe": "0.10",
            "market_cap": "29800000000",
            "operating_margin": "0.12",
            "equity_ratio": "0.716",
            "revenue_growth": "0.15",
            "op_profit_growth": "0.25",
            "dividend_yield": "0.03",
            "net_cash_ratio": "0.497",
            "week52_high_discount": "0.15",
            "current_price": "1500",
        }

    def test_operating_margin_mapped(self):
        row = self._make_full_row()
        target = EvaluationTarget.from_csv_row(row)
        assert target.financial_snapshot.operating_margin == 0.12

    def test_equity_ratio_mapped(self):
        row = self._make_full_row()
        target = EvaluationTarget.from_csv_row(row)
        assert target.financial_snapshot.equity_ratio == 0.716

    def test_revenue_growth_mapped(self):
        row = self._make_full_row()
        target = EvaluationTarget.from_csv_row(row)
        assert target.financial_snapshot.revenue_growth == 0.15

    def test_op_profit_growth_mapped_to_operating_profit_growth(self):
        """CSVの op_profit_growth が operating_profit_growth にマッピングされる。"""
        row = self._make_full_row()
        target = EvaluationTarget.from_csv_row(row)
        assert target.financial_snapshot.operating_profit_growth == 0.25

    def test_dividend_yield_mapped(self):
        row = self._make_full_row()
        target = EvaluationTarget.from_csv_row(row)
        assert target.financial_snapshot.dividend_yield == 0.03

    def test_net_cash_ratio_mapped(self):
        row = self._make_full_row()
        target = EvaluationTarget.from_csv_row(row)
        assert target.financial_snapshot.net_cash_ratio == 0.497

    def test_week52_high_discount_mapped_to_high_52w_discount(self):
        """CSVの week52_high_discount が high_52w_discount にマッピングされる。"""
        row = self._make_full_row()
        target = EvaluationTarget.from_csv_row(row)
        assert target.financial_snapshot.high_52w_discount == 0.15

    def test_current_price_mapped(self):
        row = self._make_full_row()
        target = EvaluationTarget.from_csv_row(row)
        assert target.financial_snapshot.current_price == 1500

    def test_missing_optional_fields_are_none(self):
        """CSVに含まれないオプションフィールドは None になる。"""
        row = {
            "rank": "1",
            "ticker": "1001",
            "company_name": "テスト",
            "sector": "電気機器",
            "total_score": "50.0",
            "per": "10.0",
            "pbr": "1.0",
            "roe": "0.08",
            "market_cap": "10000000000",
        }
        target = EvaluationTarget.from_csv_row(row)
        snap = target.financial_snapshot
        assert snap.operating_margin is None
        assert snap.equity_ratio is None
        assert snap.net_cash_ratio is None
        assert snap.dividend_yield is None
