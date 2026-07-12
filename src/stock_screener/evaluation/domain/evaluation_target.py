from __future__ import annotations

from dataclasses import dataclass, field

from stock_screener.discovery.domain.candidate import Candidate
from stock_screener.market_data.domain.financial_snapshot import FinancialSnapshot
from stock_screener.shared.types import Ticker


def _parse_anomaly_flags(value: str) -> list[str]:
    if not value or value.strip() == "":
        return []
    return [f.strip() for f in value.split(";") if f.strip()]


def _parse_optional_float(value: str) -> float | None:
    if not value or value.strip() == "":
        return None
    return float(value)


@dataclass(frozen=True)
class EvaluationTarget:
    """3-Gate 評価の対象銘柄。スクリーニング結果、または財務スナップショット単体から生成される。

    discovery_rank/score_total はスクリーニング(discovery)由来のメタデータであり、
    from_snapshot 経由(単銘柄指定の evaluate)で生成した場合は None になる。
    """

    ticker: Ticker
    company_name: str | None
    sector: str
    financial_snapshot: FinancialSnapshot
    discovery_rank: int | None = None
    score_total: float | None = None
    anomaly_flags: list[str] = field(default_factory=list)

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
                operating_margin=_parse_optional_float(row.get("operating_margin", "")),
                equity_ratio=_parse_optional_float(row.get("equity_ratio", "")),
                revenue_growth=_parse_optional_float(row.get("revenue_growth", "")),
                operating_profit_growth=_parse_optional_float(row.get("op_profit_growth", "")),
                dividend_yield=_parse_optional_float(row.get("dividend_yield", "")),
                net_cash_ratio=_parse_optional_float(row.get("net_cash_ratio", "")),
                high_52w_discount=_parse_optional_float(row.get("week52_high_discount", "")),
                current_price=_parse_optional_float(row.get("current_price", "")),
            ),
            discovery_rank=int(row["rank"]),
            score_total=float(row["total_score"]),
            anomaly_flags=_parse_anomaly_flags(row.get("anomaly_flags", "")),
        )

    @classmethod
    def from_snapshot(
        cls,
        ticker: Ticker,
        financial_snapshot: FinancialSnapshot,
        *,
        company_name: str | None = None,
        sector: str = "",
    ) -> EvaluationTarget:
        """財務スナップショット単体から生成する (evaluate コマンドの単銘柄指定用)。

        スクリーニング(discovery)を経由しないため discovery_rank/score_total は None になる。
        """
        return cls(
            ticker=ticker,
            company_name=company_name,
            sector=sector,
            financial_snapshot=financial_snapshot,
            discovery_rank=None,
            score_total=None,
        )
