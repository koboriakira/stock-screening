from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from stock_screener.monitoring.domain.watchlist import Watchlist

DEFAULT_DIR = Path.home() / ".local" / "share" / "stock-screener" / "monitoring"
FILENAME = "watchlist.json"
MAX_SCORE_HISTORY = 90


class WatchlistRepository:
    def __init__(self, base_dir: Path | None = None) -> None:
        self._dir = base_dir or DEFAULT_DIR
        self._path = self._dir / FILENAME

    def load(self) -> Watchlist:
        if not self._path.exists():
            return Watchlist()
        with self._path.open(encoding="utf-8") as f:
            data = json.load(f)
        return Watchlist.from_dict(data)

    def save(self, watchlist: Watchlist) -> None:
        trimmed = self._trim_score_history(watchlist)
        self._dir.mkdir(parents=True, exist_ok=True)
        with self._path.open("w", encoding="utf-8") as f:
            json.dump(trimmed.to_dict(), f, ensure_ascii=False, indent=2)

    def _trim_score_history(self, watchlist: Watchlist) -> Watchlist:
        new_entries = []
        for entry in watchlist.entries:
            if len(entry.score_history) > MAX_SCORE_HISTORY:
                trimmed_history = entry.score_history[-MAX_SCORE_HISTORY:]
                new_entries.append(replace(entry, score_history=trimmed_history))
            else:
                new_entries.append(entry)
        return Watchlist(entries=new_entries)
