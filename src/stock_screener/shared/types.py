from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal

_TICKER_PATTERN = re.compile(r"^\d{4,5}$")


@dataclass(frozen=True)
class Ticker:
    code: str

    def __init__(self, raw: str) -> None:
        code = raw.removesuffix(".T")
        if not _TICKER_PATTERN.match(code):
            msg = f"ティッカーは4-5桁の数字である必要があります: {raw}"
            raise ValueError(msg)
        object.__setattr__(self, "code", code)

    @property
    def symbol(self) -> str:
        return f"{self.code}.T"

    def __str__(self) -> str:
        return self.symbol

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Ticker):
            return NotImplemented
        return self.code == other.code

    def __hash__(self) -> int:
        return hash(self.code)


@dataclass(frozen=True)
class Money:
    amount: Decimal

    @classmethod
    def yen(cls, amount: float | Decimal) -> Money:
        return cls(amount=Decimal(str(amount)))

    def __add__(self, other: Money) -> Money:
        return Money(amount=self.amount + other.amount)

    def __sub__(self, other: Money) -> Money:
        return Money(amount=self.amount - other.amount)

    def __mul__(self, factor: float | Decimal) -> Money:
        return Money(amount=self.amount * Decimal(str(factor)))

    def __truediv__(self, divisor: float | Decimal) -> Money:
        return Money(amount=self.amount / Decimal(str(divisor)))

    def __lt__(self, other: Money) -> bool:
        return self.amount < other.amount

    def __le__(self, other: Money) -> bool:
        return self.amount <= other.amount

    def __gt__(self, other: Money) -> bool:
        return self.amount > other.amount

    def __ge__(self, other: Money) -> bool:
        return self.amount >= other.amount

    def __str__(self) -> str:
        return f"¥{self.amount:,.0f}"


@dataclass(frozen=True)
class Percentage:
    value: Decimal

    @classmethod
    def from_percent(cls, percent: float | Decimal) -> Percentage:
        return cls(value=Decimal(str(percent)) / Decimal(100))

    def to_percent(self) -> float:
        return float(self.value * Decimal(100))

    def __str__(self) -> str:
        return f"{self.to_percent():.1f}%"
