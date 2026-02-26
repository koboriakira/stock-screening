from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta


@dataclass(frozen=True)
class PriceLevel:
    price: float
    label: str

    def to_dict(self) -> dict:
        return {"price": self.price, "label": self.label}

    @classmethod
    def from_dict(cls, d: dict) -> PriceLevel:
        return cls(price=d["price"], label=d["label"])


@dataclass(frozen=True)
class KeyDate:
    date: date
    event: str
    severity: str  # "low" | "medium" | "high"

    def to_dict(self) -> dict:
        return {
            "type": "date",
            "date": self.date.isoformat(),
            "event": self.event,
            "severity": self.severity,
        }

    @classmethod
    def from_dict(cls, d: dict) -> KeyDate:
        return cls(
            date=date.fromisoformat(d["date"]),
            event=d["event"],
            severity=d["severity"],
        )


@dataclass(frozen=True)
class KeyDateRange:
    start: date
    end: date
    event: str
    severity: str

    def to_dict(self) -> dict:
        return {
            "type": "date_range",
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "event": self.event,
            "severity": self.severity,
        }

    @classmethod
    def from_dict(cls, d: dict) -> KeyDateRange:
        return cls(
            start=date.fromisoformat(d["start"]),
            end=date.fromisoformat(d["end"]),
            event=d["event"],
            severity=d["severity"],
        )


@dataclass(frozen=True)
class Catalyst:
    id: str
    description: str
    timing: str
    impact: str  # "low" | "medium" | "high"
    probability: str  # "low" | "medium" | "high"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "description": self.description,
            "timing": self.timing,
            "impact": self.impact,
            "probability": self.probability,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Catalyst:
        return cls(**d)


@dataclass(frozen=True)
class Risk:
    id: str
    description: str
    timing: str
    impact: str
    probability: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "description": self.description,
            "timing": self.timing,
            "impact": self.impact,
            "probability": self.probability,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Risk:
        return cls(**d)


def _parse_key_date(d: dict) -> KeyDate | KeyDateRange:
    if d["type"] == "date_range":
        return KeyDateRange.from_dict(d)
    return KeyDate.from_dict(d)


@dataclass(frozen=True)
class AnalysisData:
    ticker: str
    updated_at: date
    thesis: str
    supports: list[PriceLevel] = field(default_factory=list)
    resistances: list[PriceLevel] = field(default_factory=list)
    key_dates: list[KeyDate | KeyDateRange] = field(default_factory=list)
    catalysts: list[Catalyst] = field(default_factory=list)
    risks: list[Risk] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "ticker": self.ticker,
            "updated_at": self.updated_at.isoformat(),
            "thesis": self.thesis,
            "price_levels": {
                "supports": [s.to_dict() for s in self.supports],
                "resistances": [r.to_dict() for r in self.resistances],
            },
            "key_dates": [kd.to_dict() for kd in self.key_dates],
            "catalysts": [c.to_dict() for c in self.catalysts],
            "risks": [r.to_dict() for r in self.risks],
        }

    @classmethod
    def from_dict(cls, d: dict) -> AnalysisData:
        pl = d.get("price_levels", {})
        return cls(
            ticker=d["ticker"],
            updated_at=date.fromisoformat(d["updated_at"]),
            thesis=d["thesis"],
            supports=[PriceLevel.from_dict(s) for s in pl.get("supports", [])],
            resistances=[PriceLevel.from_dict(r) for r in pl.get("resistances", [])],
            key_dates=[_parse_key_date(kd) for kd in d.get("key_dates", [])],
            catalysts=[Catalyst.from_dict(c) for c in d.get("catalysts", [])],
            risks=[Risk.from_dict(r) for r in d.get("risks", [])],
        )

    # --- アラート判定メソッド ---

    def nearest_support(self, current_price: float) -> PriceLevel | None:
        """現在値より下にある最も近いサポートを返す。"""
        below = [s for s in self.supports if s.price < current_price]
        return max(below, key=lambda s: s.price) if below else None

    def nearest_resistance(self, current_price: float) -> PriceLevel | None:
        """現在値より上にある最も近いレジスタンスを返す。"""
        above = [r for r in self.resistances if r.price > current_price]
        return min(above, key=lambda r: r.price) if above else None

    def is_approaching_support(self, current_price: float, threshold_pct: float = 0.03) -> bool:
        """現在値が最寄りサポートの threshold_pct 以内にあるか。"""
        support = self.nearest_support(current_price)
        if support is None:
            return False
        distance_pct = (current_price - support.price) / support.price
        return distance_pct <= threshold_pct

    def is_approaching_resistance(self, current_price: float, threshold_pct: float = 0.03) -> bool:
        """現在値が最寄りレジスタンスの threshold_pct 以内にあるか。"""
        resistance = self.nearest_resistance(current_price)
        if resistance is None:
            return False
        distance_pct = (resistance.price - current_price) / resistance.price
        return distance_pct <= threshold_pct

    def upcoming_key_dates(
        self,
        today: date,
        lookahead_days: int = 5,
    ) -> list[KeyDate | KeyDateRange]:
        """lookahead_days 以内に到来する、または期間中の key_dates を返す。"""
        horizon = today + timedelta(days=lookahead_days)
        result: list[KeyDate | KeyDateRange] = []
        for kd in self.key_dates:
            if isinstance(kd, KeyDateRange):
                if kd.start <= horizon and kd.end >= today:
                    result.append(kd)
            elif today <= kd.date <= horizon:
                result.append(kd)
        return result
