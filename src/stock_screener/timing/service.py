from __future__ import annotations

import csv
import logging
from datetime import date
from pathlib import Path

from stock_screener.timing.domain.calendar_schedule import CalendarData
from stock_screener.timing.domain.entry_signal import evaluate_entry
from stock_screener.timing.domain.exit_rules import check_exit_conditions
from stock_screener.timing.domain.order_sheet import generate_order_sheet
from stock_screener.timing.domain.portfolio import Portfolio
from stock_screener.timing.infrastructure.calendar_repository import CalendarRepository
from stock_screener.timing.infrastructure.market_data_fetcher import fetch_market_data
from stock_screener.timing.infrastructure.portfolio_repository import PortfolioRepository

logger = logging.getLogger(__name__)

DEFAULT_ORDER_DIR = Path.home() / ".local" / "share" / "stock-screener" / "timing" / "orders"


class TimingService:
    def __init__(
        self,
        portfolio_repo: PortfolioRepository | None = None,
        calendar_repo: CalendarRepository | None = None,
    ) -> None:
        self._portfolio_repo = portfolio_repo or PortfolioRepository()
        self._calendar_repo = calendar_repo or CalendarRepository()

    def execute(
        self,
        eval_csv_path: str,
        today: date | None = None,
        output_dir: str | None = None,
    ) -> str:
        """タイミング判定のメインフロー。

        1. portfolio.json を読み込む
        2. calendar.json を読み込む
        3. eval CSV から verdict="invest" 銘柄リストを取得
        4. 各銘柄について yfinance でマーケットデータ取得 + evaluate_entry
        5. 保有銘柄についてエグジット判定
        6. オーダーシート生成

        Returns:
            オーダーシートのテキスト
        """
        if today is None:
            import datetime as _dt  # noqa: PLC0415

            today = _dt.datetime.now(tz=_dt.UTC).date()

        portfolio = self._portfolio_repo.load()
        calendar = self._calendar_repo.load()

        invest_tickers = self._load_invest_tickers(eval_csv_path)
        logger.info("invest 銘柄数: %d", len(invest_tickers))

        entry_results = self._check_entries(invest_tickers, portfolio, calendar, today)
        exit_results = self._check_exits(portfolio, today)

        order_dir = output_dir or str(DEFAULT_ORDER_DIR)
        return generate_order_sheet(entry_results, exit_results, portfolio, today, order_dir)

    def _load_invest_tickers(self, csv_path: str) -> list[dict[str, str]]:
        """eval CSV から verdict="invest" の銘柄を抽出する。"""
        path = Path(csv_path)
        with path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            return [row for row in reader if row.get("verdict", "").lower() == "invest"]

    def _check_entries(
        self,
        invest_rows: list[dict[str, str]],
        portfolio: Portfolio,
        calendar: CalendarData,
        today: date,
    ) -> list[dict]:
        """各 invest 銘柄のエントリー判定を実行する。"""
        results = []
        for row in invest_rows:
            ticker = row["ticker"]
            logger.info("エントリー判定: %s", ticker)

            market_data = fetch_market_data(ticker)
            if market_data is None:
                logger.warning("%s: マーケットデータ取得失敗、スキップ", ticker)
                results.append({
                    "ticker": ticker,
                    "sizing_result": "skip",
                    "sizing_message": "マーケットデータ取得失敗",
                    "blocker_result": "pass",
                    "blocker_details": [],
                    "signal_score": 0,
                    "signal_details": [],
                    "verdict": "skip",
                    "current_price": 0,
                })
                continue

            result = evaluate_entry(ticker, market_data, portfolio, calendar, today)
            results.append(result)

        return results

    def _check_exits(
        self,
        portfolio: Portfolio,
        today: date,
    ) -> list[dict]:
        """保有銘柄のエグジット判定を実行する。"""
        results = []
        for holding in portfolio.holdings:
            ticker = holding.ticker
            logger.info("エグジット判定: %s", ticker)

            market_data = fetch_market_data(ticker)
            if market_data is None:
                logger.warning("%s: マーケットデータ取得失敗、エグジット判定スキップ", ticker)
                continue

            current_price = market_data["current_price"]
            result = check_exit_conditions(holding, current_price, today)
            results.append(result)

        return results
