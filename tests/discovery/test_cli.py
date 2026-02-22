import csv
from unittest.mock import MagicMock, patch

import pytest

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

    def test_csv_contains_extended_columns(self, tmp_path):
        """P1-01: CSV output includes financial metrics and metadata."""
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

        with output_path.open() as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        required_columns = [
            "ticker",
            "company_name",
            "sector",
            "market_cap",
            "total_score",
            "value_score",
            "quality_score",
            "momentum_score",
            "per",
            "pbr",
            "roe",
            "operating_margin",
            "equity_ratio",
            "revenue_growth",
            "op_profit_growth",
            "dividend_yield",
            "net_cash_ratio",
            "week52_high_discount",
            "current_price",
            "screening_date",
        ]
        for col in required_columns:
            assert col in rows[0], f"Missing column: {col}"

    def test_cli_output_includes_financial_columns(self, capsys):
        """P1-01: CLI output includes market cap, dividend yield, NC ratio."""
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
        # Header should contain extended columns
        assert "PER" in captured.out
        assert "PBR" in captured.out

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


class TestCliErrorHandling:
    def test_evaluate_missing_file(self, caplog, tmp_path):
        missing = tmp_path / "nonexistent.csv"
        with (
            patch("sys.argv", ["stock-screener", "evaluate", "--input", str(missing)]),
            pytest.raises(SystemExit) as exc_info,
        ):
            main()
        assert exc_info.value.code == 1
        assert "見つかりません" in caplog.text

    def test_screen_jpx_fetch_failure(self, caplog):
        mock_jpx_cls = MagicMock()
        mock_jpx_cls.return_value.fetch.side_effect = RuntimeError("network error")
        with (
            patch("stock_screener.cli.JpxStockListFetcher", mock_jpx_cls),
            patch("sys.argv", ["stock-screener", "screen", "--test"]),
            pytest.raises(SystemExit) as exc_info,
        ):
            main()
        assert exc_info.value.code == 1
        assert "エラー" in caplog.text
