from __future__ import annotations

import json
from pathlib import Path

from stock_screener.monitoring.domain.analysis import AnalysisData

DEFAULT_DIR = Path.home() / ".local" / "share" / "stock-screener" / "analysis"


def _ticker_to_filename(ticker: str) -> str:
    """4486.T → 4486T"""
    return ticker.replace(".", "")


class AnalysisRepository:
    def __init__(self, base_dir: Path | None = None) -> None:
        self._dir = base_dir or DEFAULT_DIR

    def save(self, analysis: AnalysisData) -> Path:
        self._dir.mkdir(parents=True, exist_ok=True)
        path = self._dir / f"{_ticker_to_filename(analysis.ticker)}.json"
        with path.open("w", encoding="utf-8") as f:
            json.dump(analysis.to_dict(), f, ensure_ascii=False, indent=2)
        return path

    def load(self, ticker: str) -> AnalysisData | None:
        path = self._dir / f"{_ticker_to_filename(ticker)}.json"
        if not path.exists():
            return None
        with path.open(encoding="utf-8") as f:
            return AnalysisData.from_dict(json.load(f))

    def save_markdown(self, ticker: str, content: str) -> Path:
        self._dir.mkdir(parents=True, exist_ok=True)
        path = self._dir / f"{_ticker_to_filename(ticker)}.md"
        with path.open("w", encoding="utf-8") as f:
            f.write(content)
        return path

    def load_markdown(self, ticker: str) -> str | None:
        path = self._dir / f"{_ticker_to_filename(ticker)}.md"
        if not path.exists():
            return None
        with path.open(encoding="utf-8") as f:
            return f.read()

    def list_tickers(self) -> list[str]:
        if not self._dir.exists():
            return []
        tickers: set[str] = set()
        for path in self._dir.glob("*.json"):
            stem = path.stem
            # 4486T → 4486.T
            tickers.add(f"{stem[:-1]}.{stem[-1]}")
        return sorted(tickers)
