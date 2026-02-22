from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class WatchlistEntry:
    """ウォッチリストの1銘柄。購入前の監視対象。"""

    ticker: str
    name: str
    added_date: date
    memo: str = ""

    def to_dict(self) -> dict:
        return {
            "ticker": self.ticker,
            "name": self.name,
            "added_date": self.added_date.isoformat(),
            "memo": self.memo,
        }

    @classmethod
    def from_dict(cls, d: dict) -> WatchlistEntry:
        return cls(
            ticker=d["ticker"],
            name=d["name"],
            added_date=date.fromisoformat(d["added_date"]),
            memo=d.get("memo", ""),
        )


@dataclass
class Watchlist:
    """ウォッチリスト。購入前の監視対象銘柄の集合。"""

    entries: list[WatchlistEntry] = field(default_factory=list)

    def add(self, entry: WatchlistEntry) -> None:
        if self.find(entry.ticker) is not None:
            msg = f"Already in watchlist: {entry.ticker}"
            raise ValueError(msg)
        self.entries.append(entry)

    def remove(self, ticker: str) -> None:
        entry = self.find(ticker)
        if entry is None:
            msg = f"Not in watchlist: {ticker}"
            raise ValueError(msg)
        self.entries = [e for e in self.entries if e.ticker != ticker]

    def find(self, ticker: str) -> WatchlistEntry | None:
        for e in self.entries:
            if e.ticker == ticker:
                return e
        return None

    def to_dict(self) -> dict:
        return {
            "entries": [e.to_dict() for e in self.entries],
        }

    @classmethod
    def from_dict(cls, d: dict) -> Watchlist:
        return cls(
            entries=[WatchlistEntry.from_dict(e) for e in d.get("entries", [])],
        )
