from datetime import date
from unittest.mock import MagicMock, patch

from stock_screener.monitoring.infrastructure.report_repository import MonitoringReportRepository
from stock_screener.monitoring.service import DailyMonitoringService
from stock_screener.timing.domain.portfolio import Holding, Portfolio
from stock_screener.timing.infrastructure.portfolio_repository import PortfolioRepository


def _make_holding(**kwargs) -> Holding:
    defaults = {
        "ticker": "5599.T",
        "name": "S&J",
        "shares": 100,
        "entry_price": 1780,
        "entry_date": date(2026, 1, 15),
        "stop_loss": 1513,
        "target_price": 2670,
        "max_holding_date": date(2026, 7, 14),
    }
    defaults.update(kwargs)
    return Holding(**defaults)


def _make_portfolio(holdings: list[Holding] | None = None) -> Portfolio:
    return Portfolio(
        total_capital=1_000_000,
        cash_balance=822_000,
        holdings=holdings or [_make_holding()],
    )


class TestDailyMonitoringService:
    def test_skip_non_trading_day(self, tmp_path):
        """非営業日の場合はスキップ"""
        repo = PortfolioRepository(base_dir=tmp_path)
        repo.save(_make_portfolio())
        report_repo = MonitoringReportRepository(base_dir=tmp_path)
        service = DailyMonitoringService(
            portfolio_repo=repo,
            report_repo=report_repo,
        )
        # 2026-02-22 is Sunday
        result = service.execute(today=date(2026, 2, 22))
        assert result["skipped"] is True
        assert result["reason"] == "non_trading_day"

    def test_skip_calendar_flag(self, tmp_path):
        """skip_calendar=True の場合は営業日判定をスキップ"""
        repo = PortfolioRepository(base_dir=tmp_path)
        repo.save(_make_portfolio())
        report_repo = MonitoringReportRepository(base_dir=tmp_path)
        service = DailyMonitoringService(
            portfolio_repo=repo,
            report_repo=report_repo,
        )
        with patch(
            "stock_screener.monitoring.service.fetch_market_data",
            return_value={"current_price": 1800},
        ):
            # Sunday but skip_calendar=True
            result = service.execute(today=date(2026, 2, 22), skip_calendar=True)
        assert result["skipped"] is False

    def test_empty_portfolio(self, tmp_path):
        """保有銘柄が0件の場合"""
        repo = PortfolioRepository(base_dir=tmp_path)
        repo.save(Portfolio(total_capital=1_000_000, cash_balance=1_000_000))
        report_repo = MonitoringReportRepository(base_dir=tmp_path)
        service = DailyMonitoringService(
            portfolio_repo=repo,
            report_repo=report_repo,
        )
        with patch(
            "stock_screener.monitoring.service.is_trading_day",
            return_value=True,
        ):
            result = service.execute(today=date(2026, 3, 1))
        assert result["skipped"] is False
        assert len(result["results"]) == 0

    @patch("stock_screener.monitoring.service.fetch_market_data")
    @patch("stock_screener.monitoring.service.is_trading_day", return_value=True)
    def test_hold_action(self, mock_trading, mock_fetch, tmp_path):
        """hold 判定の場合は通知しない"""
        mock_fetch.return_value = {"current_price": 1800}
        repo = PortfolioRepository(base_dir=tmp_path)
        repo.save(_make_portfolio())
        report_repo = MonitoringReportRepository(base_dir=tmp_path)
        service = DailyMonitoringService(
            portfolio_repo=repo,
            report_repo=report_repo,
        )
        result = service.execute(today=date(2026, 3, 1))
        assert len(result["results"]) == 1
        assert result["results"][0]["action"] == "hold"
        assert result["notifications_sent"] == 0

    @patch("stock_screener.monitoring.service.send_notification")
    @patch("stock_screener.monitoring.service.fetch_market_data")
    @patch("stock_screener.monitoring.service.is_trading_day", return_value=True)
    def test_stop_loss_triggers_notification(
        self, mock_trading, mock_fetch, mock_notify, tmp_path,
    ):
        """stop_loss 判定で Slack 通知"""
        mock_fetch.return_value = {"current_price": 1500}
        mock_notify.return_value = True
        repo = PortfolioRepository(base_dir=tmp_path)
        repo.save(_make_portfolio())
        report_repo = MonitoringReportRepository(base_dir=tmp_path)
        service = DailyMonitoringService(
            portfolio_repo=repo,
            report_repo=report_repo,
        )
        result = service.execute(today=date(2026, 3, 1))
        assert result["results"][0]["action"] == "stop_loss"
        assert result["notifications_sent"] == 1
        mock_notify.assert_called_once()

    @patch("stock_screener.monitoring.service.fetch_market_data")
    @patch("stock_screener.monitoring.service.is_trading_day", return_value=True)
    def test_report_is_saved(self, mock_trading, mock_fetch, tmp_path):
        """JSON レポートが保存される"""
        mock_fetch.return_value = {"current_price": 1800}
        repo = PortfolioRepository(base_dir=tmp_path)
        repo.save(_make_portfolio())
        report_repo = MonitoringReportRepository(base_dir=tmp_path)
        service = DailyMonitoringService(
            portfolio_repo=repo,
            report_repo=report_repo,
        )
        result = service.execute(today=date(2026, 3, 1))
        assert result["report_path"] is not None
        assert result["report_path"].exists()

    @patch("stock_screener.monitoring.service.fetch_market_data")
    @patch("stock_screener.monitoring.service.is_trading_day", return_value=True)
    def test_market_data_failure_skips_holding(
        self, mock_trading, mock_fetch, tmp_path,
    ):
        """market data 取得失敗時はスキップ"""
        mock_fetch.return_value = None
        repo = PortfolioRepository(base_dir=tmp_path)
        repo.save(_make_portfolio())
        report_repo = MonitoringReportRepository(base_dir=tmp_path)
        service = DailyMonitoringService(
            portfolio_repo=repo,
            report_repo=report_repo,
        )
        result = service.execute(today=date(2026, 3, 1))
        assert len(result["results"]) == 0

    @patch("stock_screener.monitoring.service.fetch_market_data")
    @patch("stock_screener.monitoring.service.is_trading_day", return_value=True)
    def test_gate_reevaluation_with_eval_provider(
        self, mock_trading, mock_fetch, tmp_path,
    ):
        """target_hit 時に eval_provider があれば Gate 再評価を実行"""
        mock_fetch.return_value = {"current_price": 2700}
        repo = PortfolioRepository(base_dir=tmp_path)
        repo.save(_make_portfolio())
        report_repo = MonitoringReportRepository(base_dir=tmp_path)

        mock_eval_service = MagicMock()
        mock_eval_service.execute.return_value = []

        service = DailyMonitoringService(
            portfolio_repo=repo,
            report_repo=report_repo,
            eval_service=mock_eval_service,
        )
        service.execute(today=date(2026, 3, 1))
        mock_eval_service.execute.assert_called_once()
