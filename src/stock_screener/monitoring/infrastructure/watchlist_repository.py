from __future__ import annotations

import json
from pathlib import Path

from stock_screener.monitoring.domain.watchlist import Watchlist

DEFAULT_DIR = Path.home() / ".local" / "share" / "stock-screener" / "monitoring"
FILENAME = "watchlist.json"


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
        self._dir.mkdir(parents=True, exist_ok=True)
        with self._path.open("w", encoding="utf-8") as f:
            json.dump(watchlist.to_dict(), f, ensure_ascii=False, indent=2)
