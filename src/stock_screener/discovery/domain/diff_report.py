"""Screening result snapshot and diff report domain objects."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from stock_screener.discovery.domain.candidate import ScreeningResult

SCORE_CHANGE_THRESHOLD = 5.0


@dataclass(frozen=True)
class CandidateSnapshot:
    """Lightweight snapshot of a screening candidate for persistence."""

    ticker: str
    name: str
    score_total: float
    score_value: float
    score_quality: float
    score_momentum: float
    rank: int

    def to_dict(self) -> dict:
        """Serialize to dict."""
        return {
            "ticker": self.ticker,
            "name": self.name,
            "score_total": self.score_total,
            "score_value": self.score_value,
            "score_quality": self.score_quality,
            "score_momentum": self.score_momentum,
            "rank": self.rank,
        }

    @classmethod
    def from_dict(cls, data: dict) -> CandidateSnapshot:
        """Deserialize from dict."""
        return cls(
            ticker=data["ticker"],
            name=data["name"],
            score_total=data["score_total"],
            score_value=data["score_value"],
            score_quality=data["score_quality"],
            score_momentum=data["score_momentum"],
            rank=data["rank"],
        )


@dataclass(frozen=True)
class ScreeningResultSnapshot:
    """Serializable snapshot of screening results for persistence and diff."""

    execution_date: datetime
    universe_size: int
    hard_filter_passed: int
    soft_filter_passed: int
    candidates: list[CandidateSnapshot]

    def to_json(self) -> str:
        """Serialize to JSON string."""
        data = {
            "execution_date": self.execution_date.isoformat(),
            "universe_size": self.universe_size,
            "hard_filter_passed": self.hard_filter_passed,
            "soft_filter_passed": self.soft_filter_passed,
            "candidates": [c.to_dict() for c in self.candidates],
        }
        return json.dumps(data, ensure_ascii=False, indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> ScreeningResultSnapshot:
        """Deserialize from JSON string."""
        data = json.loads(json_str)
        return cls(
            execution_date=datetime.fromisoformat(data["execution_date"]),
            universe_size=data["universe_size"],
            hard_filter_passed=data["hard_filter_passed"],
            soft_filter_passed=data["soft_filter_passed"],
            candidates=[CandidateSnapshot.from_dict(c) for c in data["candidates"]],
        )

    @classmethod
    def from_screening_result(cls, result: ScreeningResult) -> ScreeningResultSnapshot:
        """Convert a ScreeningResult to a persistable snapshot."""
        candidates = [
            CandidateSnapshot(
                ticker=c.security.ticker.symbol,
                name=c.security.company_name,
                score_total=c.score.total,
                score_value=c.score.value,
                score_quality=c.score.quality,
                score_momentum=c.score.momentum,
                rank=c.rank,
            )
            for c in result.candidates
        ]
        return cls(
            execution_date=result.timestamp,
            universe_size=result.total_universe,
            hard_filter_passed=result.after_hard_filter,
            soft_filter_passed=result.after_soft_filter,
            candidates=candidates,
        )


@dataclass(frozen=True)
class ScoreChange:
    """Record of a significant score change between two snapshots."""

    ticker: str
    name: str
    old_score: float
    new_score: float
    delta: float


@dataclass(frozen=True)
class DiffReport:
    """Diff between two screening result snapshots."""

    old_date: datetime
    new_date: datetime
    old_universe_size: int
    new_universe_size: int
    new_entries: list[CandidateSnapshot]
    dropped_entries: list[CandidateSnapshot]
    score_changes: list[ScoreChange]

    @classmethod
    def compare(
        cls,
        old: ScreeningResultSnapshot,
        new: ScreeningResultSnapshot,
        *,
        top_n: int = 20,
    ) -> DiffReport:
        """Compare two snapshots and generate a diff report."""
        old_top = old.candidates[:top_n]
        new_top = new.candidates[:top_n]

        old_tickers = {c.ticker for c in old_top}
        new_tickers = {c.ticker for c in new_top}

        new_entries = [c for c in new_top if c.ticker not in old_tickers]
        dropped_entries = [c for c in old_top if c.ticker not in new_tickers]

        # Find significant score changes for common tickers
        old_by_ticker = {c.ticker: c for c in old_top}
        score_changes = []
        for c in new_top:
            if c.ticker in old_by_ticker:
                old_c = old_by_ticker[c.ticker]
                delta = c.score_total - old_c.score_total
                if abs(delta) >= SCORE_CHANGE_THRESHOLD:
                    score_changes.append(
                        ScoreChange(
                            ticker=c.ticker,
                            name=c.name,
                            old_score=old_c.score_total,
                            new_score=c.score_total,
                            delta=delta,
                        ),
                    )

        return cls(
            old_date=old.execution_date,
            new_date=new.execution_date,
            old_universe_size=old.universe_size,
            new_universe_size=new.universe_size,
            new_entries=new_entries,
            dropped_entries=dropped_entries,
            score_changes=score_changes,
        )

    def format(self) -> str:
        """Format the diff report as a human-readable string."""
        lines: list[str] = []
        lines.append("=== Screening Diff Report ===")
        lines.append(
            f"Compare: {self.new_date.strftime('%Y-%m-%d')} vs {self.old_date.strftime('%Y-%m-%d')}",
        )
        lines.append("")

        if self.new_entries:
            lines.append("[New in TOP N]")
            lines.extend(f"  + {c.ticker} {c.name}  {c.score_total:.1f}" for c in self.new_entries)
            lines.append("")

        if self.dropped_entries:
            lines.append("[Dropped from TOP N]")
            lines.extend(f"  - {c.ticker} {c.name}  {c.score_total:.1f}" for c in self.dropped_entries)
            lines.append("")

        if self.score_changes:
            lines.append(f"[Score Changes (>= {SCORE_CHANGE_THRESHOLD})]")
            for sc in self.score_changes:
                sign = "+" if sc.delta > 0 else ""
                lines.append(
                    f"  {sc.ticker} {sc.name}  {sc.old_score:.1f} -> {sc.new_score:.1f} ({sign}{sc.delta:.1f})",
                )
            lines.append("")

        lines.append("[Universe]")
        delta = self.new_universe_size - self.old_universe_size
        sign = "+" if delta > 0 else ""
        lines.append(
            f"  {self.old_universe_size} -> {self.new_universe_size} ({sign}{delta})",
        )

        return "\n".join(lines)
