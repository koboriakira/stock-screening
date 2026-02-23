from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date


@dataclass(frozen=True)
class WatchlistParams:
    """銘柄別のモニタリングパラメータ。"""

    score_threshold: int = 3
    volume_threshold: float = 1.5
    cooldown_days: int = 3

    def to_dict(self) -> dict:
        return {
            "score_threshold": self.score_threshold,
            "volume_threshold": self.volume_threshold,
            "cooldown_days": self.cooldown_days,
        }

    @classmethod
    def from_dict(cls, d: dict) -> WatchlistParams:
        return cls(
            score_threshold=d.get("score_threshold", 3),
            volume_threshold=d.get("volume_threshold", 1.5),
            cooldown_days=d.get("cooldown_days", 3),
        )


@dataclass(frozen=True)
class ScoreRecord:
    """スコア履歴の1レコード。"""

    date: date
    score: int

    def to_dict(self) -> dict:
        return {
            "date": self.date.isoformat(),
            "score": self.score,
        }

    @classmethod
    def from_dict(cls, d: dict) -> ScoreRecord:
        return cls(
            date=date.fromisoformat(d["date"]),
            score=d["score"],
        )


@dataclass(frozen=True)
class WatchlistEntry:
    """ウォッチリストの1銘柄。購入前の監視対象。"""

    ticker: str
    name: str
    added_date: date
    memo: str = ""
    registered_price: float | None = None
    last_notified_at: date | None = None
    params: WatchlistParams = field(default_factory=WatchlistParams)
    score_history: list[ScoreRecord] = field(default_factory=list)

    def to_dict(self) -> dict:
        d: dict = {
            "ticker": self.ticker,
            "name": self.name,
            "added_date": self.added_date.isoformat(),
            "memo": self.memo,
        }
        if self.registered_price is not None:
            d["registered_price"] = self.registered_price
        if self.last_notified_at is not None:
            d["last_notified_at"] = self.last_notified_at.isoformat()
        if self.params != WatchlistParams():
            d["params"] = self.params.to_dict()
        if self.score_history:
            d["score_history"] = [r.to_dict() for r in self.score_history]
        return d

    @classmethod
    def from_dict(cls, d: dict) -> WatchlistEntry:
        params_data = d.get("params")
        params = WatchlistParams.from_dict(params_data) if params_data else WatchlistParams()

        history_data = d.get("score_history", [])
        score_history = [ScoreRecord.from_dict(r) for r in history_data]

        last_notified = d.get("last_notified_at")

        return cls(
            ticker=d["ticker"],
            name=d["name"],
            added_date=date.fromisoformat(d["added_date"]),
            memo=d.get("memo", ""),
            registered_price=d.get("registered_price"),
            last_notified_at=date.fromisoformat(last_notified) if last_notified else None,
            params=params,
            score_history=score_history,
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

    def update_entry(self, ticker: str, **kwargs: object) -> Watchlist:
        """frozen な WatchlistEntry を新しいフィールド値で差し替える。"""
        entry = self.find(ticker)
        if entry is None:
            msg = f"Not in watchlist: {ticker}"
            raise ValueError(msg)
        updated = replace(entry, **kwargs)
        new_entries = [updated if e.ticker == ticker else e for e in self.entries]
        return Watchlist(entries=new_entries)

    def to_dict(self) -> dict:
        return {
            "entries": [e.to_dict() for e in self.entries],
        }

    @classmethod
    def from_dict(cls, d: dict) -> Watchlist:
        return cls(
            entries=[WatchlistEntry.from_dict(e) for e in d.get("entries", [])],
        )
