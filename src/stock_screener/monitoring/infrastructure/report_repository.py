from __future__ import annotations

import json
from datetime import date
from pathlib import Path

DEFAULT_DIR = Path.home() / ".local" / "share" / "stock-screener" / "monitoring"


class MonitoringReportRepository:
    def __init__(self, base_dir: Path | None = None) -> None:
        self._dir = base_dir or DEFAULT_DIR

    def save(self, report: dict, today: date) -> Path:
        """JSON レポートを保存する。"""
        self._dir.mkdir(parents=True, exist_ok=True)
        filename = f"{today.strftime('%Y%m%d')}_monitor.json"
        path = self._dir / filename
        with path.open("w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        return path
