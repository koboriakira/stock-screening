from __future__ import annotations

import logging
from datetime import date

from stock_screener.evaluation.domain.evaluation_target import EvaluationTarget
from stock_screener.evaluation.service import EvaluationService
from stock_screener.market_data.domain.financial_snapshot import FinancialSnapshot
from stock_screener.monitoring.domain.exit_monitor import evaluate_holding
from stock_screener.monitoring.domain.trading_day import is_trading_day
from stock_screener.monitoring.infrastructure.report_repository import MonitoringReportRepository
from stock_screener.monitoring.infrastructure.slack_notifier import format_message, send_notification
from stock_screener.shared.types import Ticker
from stock_screener.timing.infrastructure.market_data_fetcher import fetch_market_data
from stock_screener.timing.infrastructure.portfolio_repository import PortfolioRepository

logger = logging.getLogger(__name__)


class DailyMonitoringService:
    """保有銘柄の日次モニタリングサービス。"""

    def __init__(
        self,
        portfolio_repo: PortfolioRepository | None = None,
        report_repo: MonitoringReportRepository | None = None,
        eval_service: EvaluationService | None = None,
    ) -> None:
        self._portfolio_repo = portfolio_repo or PortfolioRepository()
        self._report_repo = report_repo or MonitoringReportRepository()
        self._eval_service = eval_service

    def execute(
        self,
        today: date | None = None,
        skip_calendar: bool = False,
    ) -> dict:
        """日次モニタリングのメインフロー。

        Returns:
            {
                "skipped": bool,
                "reason": str | None,
                "date": str,
                "results": list[dict],
                "notifications_sent": int,
                "report_path": Path | None,
            }
        """
        if today is None:
            import datetime as _dt  # noqa: PLC0415

            today = _dt.datetime.now(tz=_dt.UTC).date()

        if not skip_calendar and not is_trading_day(today):
            logger.info("Non-trading day: %s", today)
            return {
                "skipped": True,
                "reason": "non_trading_day",
                "date": today.isoformat(),
                "results": [],
                "notifications_sent": 0,
                "report_path": None,
            }

        portfolio = self._portfolio_repo.load()
        results = []
        notifications_sent = 0
        reeval_tickers = []

        for holding in portfolio.holdings:
            market_data = fetch_market_data(holding.ticker)
            if market_data is None:
                logger.warning("%s: market data fetch failed, skipping", holding.ticker)
                continue

            current_price = market_data["current_price"]
            result = evaluate_holding(holding, current_price, today)
            results.append(result)

            if result["needs_gate_reevaluation"]:
                reeval_tickers.append(holding.ticker)

            msg = format_message(result, today)
            if msg and send_notification(msg):
                notifications_sent += 1

        if reeval_tickers and self._eval_service:
            self._run_gate_reevaluation(reeval_tickers)

        report_data = {
            "date": today.isoformat(),
            "results": results,
            "notifications_sent": notifications_sent,
        }
        report_path = self._report_repo.save(report_data, today)

        return {
            "skipped": False,
            "reason": None,
            "date": today.isoformat(),
            "results": results,
            "notifications_sent": notifications_sent,
            "report_path": report_path,
        }

    def _run_gate_reevaluation(self, tickers: list[str]) -> None:
        """Gate 再評価を実行する。"""
        if not self._eval_service:
            return

        targets = [
            EvaluationTarget(
                ticker=Ticker(t.replace(".T", "")),
                company_name="",
                sector="",
                financial_snapshot=FinancialSnapshot(),
                score_total=0,
                discovery_rank=0,
            )
            for t in tickers
        ]
        logger.info("Gate re-evaluation: %d tickers", len(targets))
        self._eval_service.execute(targets)
