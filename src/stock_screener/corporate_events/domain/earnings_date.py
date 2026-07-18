from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EarningsDate:
    """決算発表予定日(J-Quants個人向けAPI由来)。

    個人向けAPIの制約により発表予定日のみを保持し、時刻フィールドは持たない
    (DoD要件)。時刻付きデータは法人限定のJ-Quants Proでのみ提供される。
    """

    ticker: str
    date: str  # "YYYY-MM-DD" のみ
    company_name: str | None
    fiscal_year: str | None
    fiscal_quarter: str | None

    @classmethod
    def from_jquants_entry(cls, ticker: str, entry: dict) -> EarningsDate:
        """J-Quants APIレスポンスの1銘柄分の辞書から EarningsDate を組み立てる。"""
        return cls(
            ticker=ticker,
            date=entry.get("Date", ""),
            company_name=entry.get("CoName"),
            fiscal_year=entry.get("FY"),
            fiscal_quarter=entry.get("FQ"),
        )
