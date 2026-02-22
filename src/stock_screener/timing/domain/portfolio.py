from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class Holding:
    ticker: str
    name: str
    shares: int
    entry_price: float
    entry_date: date
    stop_loss: float
    target_price: float
    max_holding_date: date
    signals_at_entry: list[str] = field(default_factory=list)
    signal_score: int = 0
    trailing_count: int = 0
    extension_count: int = 0
    force_sell_flag: bool = False
    force_sell_reason: str | None = None

    def to_dict(self) -> dict:
        return {
            "ticker": self.ticker,
            "name": self.name,
            "shares": self.shares,
            "entry_price": self.entry_price,
            "entry_date": self.entry_date.isoformat(),
            "stop_loss": self.stop_loss,
            "target_price": self.target_price,
            "max_holding_date": self.max_holding_date.isoformat(),
            "signals_at_entry": self.signals_at_entry,
            "signal_score": self.signal_score,
            "trailing_count": self.trailing_count,
            "extension_count": self.extension_count,
            "force_sell_flag": self.force_sell_flag,
            "force_sell_reason": self.force_sell_reason,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Holding:
        return cls(
            ticker=d["ticker"],
            name=d["name"],
            shares=d["shares"],
            entry_price=d["entry_price"],
            entry_date=date.fromisoformat(d["entry_date"]),
            stop_loss=d["stop_loss"],
            target_price=d["target_price"],
            max_holding_date=date.fromisoformat(d["max_holding_date"]),
            signals_at_entry=d.get("signals_at_entry", []),
            signal_score=d.get("signal_score", 0),
            trailing_count=d.get("trailing_count", 0),
            extension_count=d.get("extension_count", 0),
            force_sell_flag=d.get("force_sell_flag", False),
            force_sell_reason=d.get("force_sell_reason"),
        )


@dataclass(frozen=True)
class TradeRecord:
    action: str
    ticker: str
    shares: int
    price: float
    date: date
    reason: str

    def to_dict(self) -> dict:
        return {
            "action": self.action,
            "ticker": self.ticker,
            "shares": self.shares,
            "price": self.price,
            "date": self.date.isoformat(),
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, d: dict) -> TradeRecord:
        return cls(
            action=d["action"],
            ticker=d["ticker"],
            shares=d["shares"],
            price=d["price"],
            date=date.fromisoformat(d["date"]),
            reason=d["reason"],
        )


@dataclass
class Portfolio:
    total_capital: float
    cash_balance: float
    holdings: list[Holding] = field(default_factory=list)
    history: list[TradeRecord] = field(default_factory=list)

    def find_holding(self, ticker: str) -> Holding | None:
        for h in self.holdings:
            if h.ticker == ticker:
                return h
        return None

    def to_dict(self) -> dict:
        return {
            "total_capital": self.total_capital,
            "cash_balance": self.cash_balance,
            "holdings": [h.to_dict() for h in self.holdings],
            "history": [r.to_dict() for r in self.history],
        }

    @classmethod
    def from_dict(cls, d: dict) -> Portfolio:
        return cls(
            total_capital=d["total_capital"],
            cash_balance=d["cash_balance"],
            holdings=[Holding.from_dict(h) for h in d.get("holdings", [])],
            history=[TradeRecord.from_dict(r) for r in d.get("history", [])],
        )
