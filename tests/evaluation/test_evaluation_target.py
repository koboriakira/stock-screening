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
