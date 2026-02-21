from __future__ import annotations

from dataclasses import dataclass

from stock_screener.market_data.domain.security import Security
from stock_screener.shared.types import Ticker


@dataclass
class Universe:
    securities: list[Security]

    @classmethod
    def from_jpx_data(cls, jpx_data: list[dict]) -> Universe:
        securities = [
            Security(
                ticker=Ticker(item["ticker"]),
                company_name=item["company_name"],
                sector=item["sector"],
            )
            for item in jpx_data
        ]
        return cls(securities=securities)

    def limit(self, n: int) -> Universe:
        return Universe(securities=self.securities[:n])

    def __len__(self) -> int:
        return len(self.securities)
