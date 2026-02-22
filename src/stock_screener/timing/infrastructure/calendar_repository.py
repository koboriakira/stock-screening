from __future__ import annotations

import json
from pathlib import Path

from stock_screener.timing.domain.calendar_schedule import CalendarData

DEFAULT_PATH = Path(__file__).resolve().parents[3] / "data" / "calendar.json"


class CalendarRepository:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path or DEFAULT_PATH

    def load(self) -> CalendarData:
        if not self._path.exists():
            return CalendarData(tickers={})
        with self._path.open(encoding="utf-8") as f:
            data = json.load(f)
        return CalendarData.from_dict(data)

    def save(self, calendar: CalendarData) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("w", encoding="utf-8") as f:
            json.dump(calendar.to_dict(), f, ensure_ascii=False, indent=2)
