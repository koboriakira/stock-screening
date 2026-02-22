from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class EarningsScheduleEntry:
    quarter: str
    announced_date: str | None
    next_date: str | None
    is_confirmed: bool = False

    def to_dict(self) -> dict:
        return {
            "quarter": self.quarter,
            "announced_date": self.announced_date,
            "next_date": self.next_date,
            "is_confirmed": self.is_confirmed,
        }

    @classmethod
    def from_dict(cls, d: dict) -> EarningsScheduleEntry:
        return cls(
            quarter=d["quarter"],
            announced_date=d.get("announced_date"),
            next_date=d.get("next_date"),
            is_confirmed=d.get("is_confirmed", False),
        )


@dataclass(frozen=True)
class DividendInfo:
    record_date: str | None = None
    amount_per_share: float | None = None

    def to_dict(self) -> dict:
        return {
            "record_date": self.record_date,
            "amount_per_share": self.amount_per_share,
        }

    @classmethod
    def from_dict(cls, d: dict) -> DividendInfo:
        return cls(
            record_date=d.get("record_date"),
            amount_per_share=d.get("amount_per_share"),
        )


@dataclass(frozen=True)
class TickerCalendar:
    name: str
    fiscal_year_end: str
    earnings_schedule: list[EarningsScheduleEntry] = field(default_factory=list)
    dividend: DividendInfo = field(default_factory=DividendInfo)

    def latest_earnings(self) -> EarningsScheduleEntry | None:
        if not self.earnings_schedule:
            return None
        return self.earnings_schedule[-1]

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "fiscal_year_end": self.fiscal_year_end,
            "earnings_schedule": [e.to_dict() for e in self.earnings_schedule],
            "dividend": self.dividend.to_dict(),
        }

    @classmethod
    def from_dict(cls, d: dict) -> TickerCalendar:
        return cls(
            name=d["name"],
            fiscal_year_end=d["fiscal_year_end"],
            earnings_schedule=[
                EarningsScheduleEntry.from_dict(e) for e in d.get("earnings_schedule", [])
            ],
            dividend=DividendInfo.from_dict(d.get("dividend", {})),
        )


@dataclass
class CalendarData:
    tickers: dict[str, TickerCalendar] = field(default_factory=dict)

    def get(self, ticker: str) -> TickerCalendar | None:
        return self.tickers.get(ticker)

    def to_dict(self) -> dict:
        return {
            "tickers": {k: v.to_dict() for k, v in self.tickers.items()},
        }

    @classmethod
    def from_dict(cls, d: dict) -> CalendarData:
        return cls(
            tickers={
                k: TickerCalendar.from_dict(v) for k, v in d.get("tickers", {}).items()
            },
        )
