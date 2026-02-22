"""Tests for screening result snapshot and diff report."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from stock_screener.discovery.domain.candidate import Candidate, ScreeningResult
from stock_screener.discovery.domain.diff_report import (
    CandidateSnapshot,
    DiffReport,
    ScreeningResultSnapshot,
)
from stock_screener.discovery.domain.scoring import ScoreResult
from stock_screener.market_data.domain.financial_snapshot import FinancialSnapshot
from stock_screener.market_data.domain.security import Security
from stock_screener.shared.types import Ticker


def _make_snapshot(
    execution_date: datetime | None = None,
    candidates: list[CandidateSnapshot] | None = None,
    universe_size: int = 1000,
    hard_filter_passed: int = 500,
    soft_filter_passed: int = 100,
) -> ScreeningResultSnapshot:
    if execution_date is None:
        execution_date = datetime(2026, 2, 21, 14, 0, tzinfo=UTC)
    if candidates is None:
        candidates = []
    return ScreeningResultSnapshot(
        execution_date=execution_date,
        universe_size=universe_size,
        hard_filter_passed=hard_filter_passed,
        soft_filter_passed=soft_filter_passed,
        candidates=candidates,
    )


def _make_candidate(
    ticker: str = "1001.T",
    name: str = "Test Corp",
    score_total: float = 75.0,
    score_value: float = 70.0,
    score_quality: float = 80.0,
    score_momentum: float = 75.0,
    rank: int = 1,
) -> CandidateSnapshot:
    return CandidateSnapshot(
        ticker=ticker,
        name=name,
        score_total=score_total,
        score_value=score_value,
        score_quality=score_quality,
        score_momentum=score_momentum,
        rank=rank,
    )


class TestCandidateSnapshot:
    def test_create(self):
        c = _make_candidate()
        assert c.ticker == "1001.T"
        assert c.score_total == 75.0
        assert c.rank == 1

    def test_to_dict(self):
        c = _make_candidate()
        d = c.to_dict()
        assert d["ticker"] == "1001.T"
        assert d["score_total"] == 75.0

    def test_from_dict(self):
        d = {
            "ticker": "2002.T",
            "name": "Corp B",
            "score_total": 80.0,
            "score_value": 70.0,
            "score_quality": 85.0,
            "score_momentum": 78.0,
            "rank": 2,
        }
        c = CandidateSnapshot.from_dict(d)
        assert c.ticker == "2002.T"
        assert c.score_total == 80.0
        assert c.rank == 2


class TestScreeningResultSnapshot:
    def test_create(self):
        snap = _make_snapshot()
        assert snap.universe_size == 1000
        assert snap.hard_filter_passed == 500

    def test_to_json_and_back(self):
        candidates = [
            _make_candidate(ticker="1001.T", rank=1),
            _make_candidate(ticker="1002.T", rank=2, score_total=70.0),
        ]
        snap = _make_snapshot(candidates=candidates)

        json_str = snap.to_json()
        parsed = json.loads(json_str)
        assert parsed["universe_size"] == 1000
        assert len(parsed["candidates"]) == 2

        restored = ScreeningResultSnapshot.from_json(json_str)
        assert restored.universe_size == snap.universe_size
        assert len(restored.candidates) == 2
        assert restored.candidates[0].ticker == "1001.T"

    def test_from_screening_result(self):
        """ScreeningResult -> ScreeningResultSnapshot conversion."""
        sec = Security(
            ticker=Ticker("1001"),
            company_name="Test Corp",
            sector="Electronics",
        )
        sec.financial_snapshot = FinancialSnapshot(market_cap=10_000_000_000)
        result = ScreeningResult(
            candidates=[
                Candidate(
                    security=sec,
                    score=ScoreResult(value=70.0, quality=80.0, momentum=75.0, total=75.0),
                    rank=1,
                ),
            ],
            total_universe=1000,
            after_hard_filter=500,
            after_soft_filter=100,
            timestamp=datetime(2026, 2, 21, 14, 0, tzinfo=UTC),
        )

        snap = ScreeningResultSnapshot.from_screening_result(result)
        assert snap.universe_size == 1000
        assert len(snap.candidates) == 1
        assert snap.candidates[0].ticker == "1001.T"
        assert snap.candidates[0].score_total == 75.0


class TestDiffReport:
    def test_new_entries(self):
        """Detect new entries in top N."""
        old = _make_snapshot(
            candidates=[
                _make_candidate(ticker="1001.T", rank=1),
                _make_candidate(ticker="1002.T", rank=2),
            ],
        )
        new = _make_snapshot(
            candidates=[
                _make_candidate(ticker="1001.T", rank=1),
                _make_candidate(ticker="1003.T", rank=2),
            ],
        )

        diff = DiffReport.compare(old, new, top_n=20)
        assert len(diff.new_entries) == 1
        assert diff.new_entries[0].ticker == "1003.T"

    def test_dropped_entries(self):
        """Detect dropped entries from top N."""
        old = _make_snapshot(
            candidates=[
                _make_candidate(ticker="1001.T", rank=1),
                _make_candidate(ticker="1002.T", rank=2),
            ],
        )
        new = _make_snapshot(
            candidates=[
                _make_candidate(ticker="1001.T", rank=1),
                _make_candidate(ticker="1003.T", rank=2),
            ],
        )

        diff = DiffReport.compare(old, new, top_n=20)
        assert len(diff.dropped_entries) == 1
        assert diff.dropped_entries[0].ticker == "1002.T"

    def test_score_changes(self):
        """Detect significant score changes (>= 5 points)."""
        old = _make_snapshot(
            candidates=[
                _make_candidate(ticker="1001.T", rank=1, score_total=75.0),
                _make_candidate(ticker="1002.T", rank=2, score_total=70.0),
            ],
        )
        new = _make_snapshot(
            candidates=[
                _make_candidate(ticker="1001.T", rank=1, score_total=80.5),
                _make_candidate(ticker="1002.T", rank=2, score_total=69.0),
            ],
        )

        diff = DiffReport.compare(old, new, top_n=20)
        assert len(diff.score_changes) == 1
        change = diff.score_changes[0]
        assert change.ticker == "1001.T"
        assert change.old_score == 75.0
        assert change.new_score == 80.5
        assert abs(change.delta - 5.5) < 0.01

    def test_universe_change(self):
        """Track universe size changes."""
        old = _make_snapshot(universe_size=1000)
        new = _make_snapshot(universe_size=1010)

        diff = DiffReport.compare(old, new, top_n=20)
        assert diff.old_universe_size == 1000
        assert diff.new_universe_size == 1010

    def test_no_changes(self):
        """Identical snapshots produce empty diff."""
        candidates = [_make_candidate(ticker="1001.T", rank=1)]
        old = _make_snapshot(candidates=candidates)
        new = _make_snapshot(candidates=candidates)

        diff = DiffReport.compare(old, new, top_n=20)
        assert len(diff.new_entries) == 0
        assert len(diff.dropped_entries) == 0
        assert len(diff.score_changes) == 0

    def test_format_report(self):
        """DiffReport can be formatted as string."""
        old = _make_snapshot(
            execution_date=datetime(2026, 2, 20, 14, 0, tzinfo=UTC),
            universe_size=1000,
            candidates=[
                _make_candidate(ticker="1001.T", name="Corp A", rank=1, score_total=75.0),
                _make_candidate(ticker="1002.T", name="Corp B", rank=2, score_total=70.0),
            ],
        )
        new = _make_snapshot(
            execution_date=datetime(2026, 2, 21, 14, 0, tzinfo=UTC),
            universe_size=1010,
            candidates=[
                _make_candidate(ticker="1001.T", name="Corp A", rank=1, score_total=80.5),
                _make_candidate(ticker="1003.T", name="Corp C", rank=2, score_total=72.0),
            ],
        )

        diff = DiffReport.compare(old, new, top_n=20)
        report = diff.format()
        assert "2026-02-21" in report
        assert "2026-02-20" in report
        assert "Corp C" in report
        assert "Corp B" in report
