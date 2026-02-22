import csv
from datetime import date
from unittest.mock import patch

from stock_screener.timing.domain.portfolio import Portfolio
from stock_screener.timing.infrastructure.calendar_repository import CalendarRepository
from stock_screener.timing.infrastructure.portfolio_repository import PortfolioRepository
from stock_screener.timing.service import TimingService


def _write_eval_csv(path, rows):
    fieldnames = ["rank", "ticker", "company_name", "verdict", "gate1", "gate2", "gate3", "score_total"]
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _mock_market_data(_ticker):
    return {
        "current_price": 1780,
        "ma25": 1800,
        "avg_volume_5d": 10000,
        "is_stop_limit": False,
    }


class TestTimingService:
    def test_execute_with_invest_tickers(self, tmp_path):
        """invest 銘柄に対してエントリー判定が実行されること"""
        eval_csv = tmp_path / "eval.csv"
        _write_eval_csv(eval_csv, [
            {
                "rank": 1, "ticker": "5599.T", "company_name": "S&J",
                "verdict": "invest", "gate1": "PASS", "gate2": "PASS",
                "gate3": "PASS", "score_total": 80,
            },
            {
                "rank": 2, "ticker": "9999.T", "company_name": "REJECT",
                "verdict": "reject", "gate1": "FAIL", "gate2": "PASS",
                "gate3": "PASS", "score_total": 70,
            },
        ])

        portfolio = Portfolio(total_capital=1_000_000, cash_balance=1_000_000)
        portfolio_repo = PortfolioRepository(base_dir=tmp_path)
        portfolio_repo.save(portfolio)

        calendar_repo = CalendarRepository(path=tmp_path / "calendar.json")

        service = TimingService(
            portfolio_repo=portfolio_repo,
            calendar_repo=calendar_repo,
        )

        with patch(
            "stock_screener.timing.service.fetch_market_data",
            side_effect=_mock_market_data,
        ):
            text = service.execute(
                str(eval_csv),
                today=date(2026, 2, 22),
                output_dir=str(tmp_path / "orders"),
            )

        assert "5599.T" in text
        assert "9999.T" not in text  # reject は含まれない

    def test_execute_with_empty_csv(self, tmp_path):
        """空のCSVでもエラーなく実行されること"""
        eval_csv = tmp_path / "eval.csv"
        _write_eval_csv(eval_csv, [])

        portfolio = Portfolio(total_capital=1_000_000, cash_balance=1_000_000)
        portfolio_repo = PortfolioRepository(base_dir=tmp_path)
        portfolio_repo.save(portfolio)
        calendar_repo = CalendarRepository(path=tmp_path / "calendar.json")

        service = TimingService(
            portfolio_repo=portfolio_repo,
            calendar_repo=calendar_repo,
        )

        text = service.execute(
            str(eval_csv),
            today=date(2026, 2, 22),
            output_dir=str(tmp_path / "orders"),
        )

        assert "2026-02-22" in text

    def test_json_output_is_created(self, tmp_path):
        """JSONファイルが出力されること"""
        eval_csv = tmp_path / "eval.csv"
        _write_eval_csv(eval_csv, [
            {
                "rank": 1, "ticker": "5599.T", "company_name": "S&J",
                "verdict": "invest", "gate1": "PASS", "gate2": "PASS",
                "gate3": "PASS", "score_total": 80,
            },
        ])

        portfolio = Portfolio(total_capital=1_000_000, cash_balance=1_000_000)
        portfolio_repo = PortfolioRepository(base_dir=tmp_path)
        portfolio_repo.save(portfolio)
        calendar_repo = CalendarRepository(path=tmp_path / "calendar.json")

        service = TimingService(
            portfolio_repo=portfolio_repo,
            calendar_repo=calendar_repo,
        )

        order_dir = tmp_path / "orders"
        with patch(
            "stock_screener.timing.service.fetch_market_data",
            side_effect=_mock_market_data,
        ):
            service.execute(
                str(eval_csv),
                today=date(2026, 2, 22),
                output_dir=str(order_dir),
            )

        json_path = order_dir / "20260222_order.json"
        assert json_path.exists()

    def test_execute_with_eval_detail_csv(self, tmp_path):
        """eval_detail形式(1銘柄複数行)でも重複なくエントリー判定されること"""
        eval_csv = tmp_path / "eval_detail.csv"
        fieldnames = [
            "rank", "ticker", "company_name", "sector",
            "verdict", "score_total", "gate", "check_id",
            "check_status", "check_description", "check_detail",
        ]
        with eval_csv.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            # 5599.T が invest で3行
            for check_id in ["1-1", "1-2", "2A-2"]:
                writer.writerow({
                    "rank": 3, "ticker": "5599.T",
                    "company_name": "S&J", "sector": "情報・通信業",
                    "verdict": "invest", "score_total": 78.51,
                    "gate": "Gate1", "check_id": check_id,
                    "check_status": "pass",
                    "check_description": "テスト", "check_detail": "",
                })
            # 4377.T が watchlist で2行
            for check_id in ["1-1", "1-2"]:
                writer.writerow({
                    "rank": 2, "ticker": "4377.T",
                    "company_name": "ワンキャリア", "sector": "情報・通信業",
                    "verdict": "watchlist", "score_total": 78.53,
                    "gate": "Gate1", "check_id": check_id,
                    "check_status": "pass",
                    "check_description": "テスト", "check_detail": "",
                })

        portfolio = Portfolio(total_capital=1_000_000, cash_balance=1_000_000)
        portfolio_repo = PortfolioRepository(base_dir=tmp_path)
        portfolio_repo.save(portfolio)
        calendar_repo = CalendarRepository(path=tmp_path / "calendar.json")

        service = TimingService(
            portfolio_repo=portfolio_repo,
            calendar_repo=calendar_repo,
        )

        with patch(
            "stock_screener.timing.service.fetch_market_data",
            side_effect=_mock_market_data,
        ) as mock_fetch:
            text = service.execute(
                str(eval_csv),
                today=date(2026, 2, 22),
                output_dir=str(tmp_path / "orders"),
            )

        # 5599.T は1回だけ fetch されること(重複なし)
        tickers_called = [call.args[0] for call in mock_fetch.call_args_list]
        assert tickers_called.count("5599.T") == 1
        assert "5599.T" in text
        # watchlist の 4377.T は含まれない
        assert "4377.T" not in text
