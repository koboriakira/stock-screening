from __future__ import annotations

from dataclasses import dataclass

from stock_screener.market_data.domain.security import Security
from stock_screener.shared.types import Ticker


@dataclass
class Universe:
    """スクリーニング対象のユニバース(銘柄群)。

    JPX 銘柄リストから生成され、スクリーニング対象の全銘柄を保持する。
    """

    securities: list[Security]

    @classmethod
    def from_jpx_data(cls, jpx_data: list[dict]) -> Universe:
        """JPX 銘柄リストのデータからユニバースを生成する。"""
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
        """先頭 n 銘柄に制限した新しいユニバースを返す。"""
        return Universe(securities=self.securities[:n])

    def __len__(self) -> int:
        return len(self.securities)
