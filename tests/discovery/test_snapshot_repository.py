"""Tests for snapshot file repository."""

from __future__ import annotations

from datetime import UTC, datetime

from stock_screener.discovery.domain.diff_report import (
    CandidateSnapshot,
    ScreeningResultSnapshot,
)
from stock_screener.discovery.infrastructure.snapshot_repository import (
    FileSnapshotRepository,
)


def _make_snapshot(
    execution_date: datetime | None = None,
) -> ScreeningResultSnapshot:
    if execution_date is None:
        execution_date = datetime(2026, 2, 21, 14, 0, tzinfo=UTC)
    return ScreeningResultSnapshot(
        execution_date=execution_date,
        universe_size=1000,
        hard_filter_passed=500,
        soft_filter_passed=100,
        candidates=[
            CandidateSnapshot(
                ticker="1001.T",
                name="Corp A",
                score_total=75.0,
                score_value=70.0,
                score_quality=80.0,
                score_momentum=75.0,
                rank=1,
            ),
        ],
    )


class TestFileSnapshotRepository:
    def test_save_and_load(self, tmp_path):
        repo = FileSnapshotRepository(base_dir=tmp_path)
        snap = _make_snapshot()

        repo.save(snap)

        loaded = repo.load_latest()
        assert loaded is not None
        assert loaded.universe_size == 1000
        assert len(loaded.candidates) == 1
        assert loaded.candidates[0].ticker == "1001.T"

    def test_load_latest_returns_most_recent(self, tmp_path):
        repo = FileSnapshotRepository(base_dir=tmp_path)
        snap_old = _make_snapshot(
            execution_date=datetime(2026, 2, 20, 10, 0, tzinfo=UTC),
        )
        snap_new = _make_snapshot(
            execution_date=datetime(2026, 2, 21, 14, 0, tzinfo=UTC),
        )

        repo.save(snap_old)
        repo.save(snap_new)

        latest = repo.load_latest()
        assert latest is not None
        assert latest.execution_date == datetime(2026, 2, 21, 14, 0, tzinfo=UTC)

    def test_load_latest_returns_none_when_empty(self, tmp_path):
        repo = FileSnapshotRepository(base_dir=tmp_path)
        assert repo.load_latest() is None

    def test_load_previous(self, tmp_path):
        repo = FileSnapshotRepository(base_dir=tmp_path)
        snap1 = _make_snapshot(
            execution_date=datetime(2026, 2, 19, 10, 0, tzinfo=UTC),
        )
        snap2 = _make_snapshot(
            execution_date=datetime(2026, 2, 20, 10, 0, tzinfo=UTC),
        )
        snap3 = _make_snapshot(
            execution_date=datetime(2026, 2, 21, 14, 0, tzinfo=UTC),
        )

        repo.save(snap1)
        repo.save(snap2)
        repo.save(snap3)

        prev = repo.load_previous()
        assert prev is not None
        assert prev.execution_date == datetime(2026, 2, 20, 10, 0, tzinfo=UTC)

    def test_load_previous_returns_none_when_only_one(self, tmp_path):
        repo = FileSnapshotRepository(base_dir=tmp_path)
        repo.save(_make_snapshot())

        assert repo.load_previous() is None

    def test_list_snapshots(self, tmp_path):
        repo = FileSnapshotRepository(base_dir=tmp_path)
        repo.save(
            _make_snapshot(execution_date=datetime(2026, 2, 20, 10, 0, tzinfo=UTC)),
        )
        repo.save(
            _make_snapshot(execution_date=datetime(2026, 2, 21, 14, 0, tzinfo=UTC)),
        )

        files = repo.list_snapshots()
        assert len(files) == 2
