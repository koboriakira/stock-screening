from __future__ import annotations

from dataclasses import dataclass

from stock_screener.discovery.domain.candidate import Candidate
from stock_screener.market_data.domain.financial_snapshot import FinancialSnapshot
from stock_screener.shared.types import Ticker


def _parse_optional_float(value: str) -> float | None:
    if not value or value.strip() == "":
        return None
    return float(value)


@dataclass(frozen=True)
class EvaluationTarget:
    """3-Gate 評価の対象銘柄。スクリーニング結果から生成される。"""

    ticker: Ticker
    company_name: str
    sector: str
    financial_snapshot: FinancialSnapshot
    discovery_rank: int
    score_total: float

    @classmethod
    def from_candidate(cls, candidate: Candidate) -> EvaluationTarget:
        return cls(
            ticker=candidate.security.ticker,
            company_name=candidate.security.company_name,
            sector=candidate.security.sector,
            financial_snapshot=candidate.security.financial_snapshot,
            discovery_rank=candidate.rank,
            score_total=candidate.score.total,
        )

    @classmethod
    def from_csv_row(cls, row: dict[str, str]) -> EvaluationTarget:
        return cls(
            ticker=Ticker(row["ticker"]),
            company_name=row["company_name"],
            sector=row["sector"],
            financial_snapshot=FinancialSnapshot(
                per=_parse_optional_float(row.get("per", "")),
                pbr=_parse_optional_float(row.get("pbr", "")),
                roe=_parse_optional_float(row.get("roe", "")),
                market_cap=_parse_optional_float(row.get("market_cap", "")),
            ),
            discovery_rank=int(row["rank"]),
            score_total=float(row["total_score"]),
        )
