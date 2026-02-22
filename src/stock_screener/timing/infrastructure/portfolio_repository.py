from __future__ import annotations

import json
from pathlib import Path

from stock_screener.timing.domain.portfolio import Portfolio

DEFAULT_DIR = Path.home() / ".local" / "share" / "stock-screener" / "timing"
FILENAME = "portfolio.json"


class PortfolioRepository:
    def __init__(self, base_dir: Path | None = None) -> None:
        self._dir = base_dir or DEFAULT_DIR
        self._path = self._dir / FILENAME

    def load(self) -> Portfolio:
        if not self._path.exists():
            return Portfolio(total_capital=0, cash_balance=0)
        with self._path.open(encoding="utf-8") as f:
            data = json.load(f)
        return Portfolio.from_dict(data)

    def save(self, portfolio: Portfolio) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        with self._path.open("w", encoding="utf-8") as f:
            json.dump(portfolio.to_dict(), f, ensure_ascii=False, indent=2)
