import csv
from unittest.mock import patch

from stock_screener.cli import main
from stock_screener.market_data.domain.financial_snapshot import FinancialSnapshot


def _make_mock_jpx_data():
    return [
        {"ticker": "1001", "company_name": "テスト株A", "sector": "電気機器", "market": "プライム"},
        {"ticker": "1002", "company_name": "テスト株B", "sector": "機械", "market": "スタンダード"},
    ]


def _make_mock_snapshot(**kwargs):
    defaults = {
        "market_cap": 10_000_000_000,
        "avg_trading_value": 50_000_000,
        "per": 10.0,
        "pbr": 0.8,
        "roe": 0.10,
        "operating_margin": 0.08,
        "equity_ratio": 0.40,
        "revenue_growth": 0.10,
        "dividend_yield": 0.02,
        "high_52w_discount": 0.15,
        "net_cash_ratio": 0.20,
        "current_price": 1500,
    }
    defaults.update(kwargs)
    return FinancialSnapshot(**defaults)


class TestCli:
    def test_screen_command_outputs_to_stdout(self, capsys):
        with (
            patch("stock_screener.cli.JpxStockListFetcher") as mock_jpx_cls,
            patch("stock_screener.cli.YFinanceSecurityRepository") as mock_repo_cls,
            patch("sys.argv", ["stock-screener", "screen", "--top", "10"]),
        ):
            mock_jpx_cls.return_value.fetch.return_value = _make_mock_jpx_data()
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_financial_snapshot.return_value = _make_mock_snapshot()

            main()

        captured = capsys.readouterr()
        assert "テスト株A" in captured.out or "テスト株B" in captured.out

    def test_screen_command_outputs_csv(self, tmp_path):
        output_path = tmp_path / "result.csv"

        with (
            patch("stock_screener.cli.JpxStockListFetcher") as mock_jpx_cls,
            patch("stock_screener.cli.YFinanceSecurityRepository") as mock_repo_cls,
            patch("sys.argv", ["stock-screener", "screen", "--top", "10", "--output", str(output_path)]),
        ):
            mock_jpx_cls.return_value.fetch.return_value = _make_mock_jpx_data()
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_financial_snapshot.return_value = _make_mock_snapshot()

            main()

        assert output_path.exists()
        with output_path.open() as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) >= 1
        assert "ticker" in rows[0]
        assert "total_score" in rows[0]

    def test_screen_test_mode(self):
        mock_jpx_data = [
            {"ticker": str(i).zfill(4), "company_name": f"会社{i}", "sector": "電気機器", "market": "プライム"}
            for i in range(1000, 1020)
        ]

        with (
            patch("stock_screener.cli.JpxStockListFetcher") as mock_jpx_cls,
            patch("stock_screener.cli.YFinanceSecurityRepository") as mock_repo_cls,
            patch("sys.argv", ["stock-screener", "screen", "--test"]),
        ):
            mock_jpx_cls.return_value.fetch.return_value = mock_jpx_data
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_financial_snapshot.return_value = _make_mock_snapshot()

            main()
