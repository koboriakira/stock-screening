"""File-based repository for screening result snapshots."""

from __future__ import annotations

import logging
from pathlib import Path

from stock_screener.discovery.domain.diff_report import ScreeningResultSnapshot

logger = logging.getLogger(__name__)

DEFAULT_SNAPSHOT_DIR = Path.home() / ".cache" / "stock-screener" / "results"


class FileSnapshotRepository:
    """Persist and load screening result snapshots as JSON files."""

    def __init__(self, base_dir: Path | None = None) -> None:
        self._base_dir = base_dir or DEFAULT_SNAPSHOT_DIR

    def save(self, snapshot: ScreeningResultSnapshot) -> Path:
        """Save a snapshot to a JSON file. Returns the file path."""
        self._base_dir.mkdir(parents=True, exist_ok=True)
        filename = f"screening_{snapshot.execution_date.strftime('%Y%m%d_%H%M%S')}.json"
        path = self._base_dir / filename
        path.write_text(snapshot.to_json(), encoding="utf-8")
        logger.info("Snapshot saved: %s", path)
        return path

    def load_latest(self) -> ScreeningResultSnapshot | None:
        """Load the most recent snapshot."""
        files = self.list_snapshots()
        if not files:
            return None
        return self._load_file(files[-1])

    def load_previous(self) -> ScreeningResultSnapshot | None:
        """Load the second most recent snapshot (for diff)."""
        files = self.list_snapshots()
        if len(files) < 2:
            return None
        return self._load_file(files[-2])

    def list_snapshots(self) -> list[Path]:
        """List all snapshot files sorted by name (oldest first)."""
        if not self._base_dir.exists():
            return []
        return sorted(self._base_dir.glob("screening_*.json"))

    def _load_file(self, path: Path) -> ScreeningResultSnapshot:
        """Load a snapshot from a JSON file."""
        json_str = path.read_text(encoding="utf-8")
        return ScreeningResultSnapshot.from_json(json_str)
