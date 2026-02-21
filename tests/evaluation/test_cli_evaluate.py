from __future__ import annotations

import csv
from unittest.mock import patch

from stock_screener.cli import main
from stock_screener.evaluation.infrastructure.stub_provider import StubEvaluationDataProvider


def _write_screen_csv(path, rows):
    fieldnames = ["rank", "ticker", "company_name", "sector", "total_score", "per", "pbr", "roe", "market_cap"]
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _make_screen_csv(tmp_path):
    csv_path = tmp_path / "screen.csv"
    _write_screen_csv(csv_path, [
        {
            "rank": "1", "ticker": "1001", "company_name": "テスト株A", "sector": "電気機器",
            "total_score": "75.0", "per": "8.0", "pbr": "0.7", "roe": "0.10", "market_cap": "10000000000",
        },
        {
            "rank": "2", "ticker": "1002", "company_name": "テスト株B", "sector": "機械",
            "total_score": "60.0", "per": "12.0", "pbr": "1.2", "roe": "", "market_cap": "8000000000",
        },
    ])
    return csv_path


def _patch_provider():
    """CLIがYFinanceEvaluationDataProviderを使うため、yfinance呼び出しを防ぐモック。"""
    return patch(
        "stock_screener.cli.YFinanceEvaluationDataProvider",
        return_value=StubEvaluationDataProvider(),
    )


class TestCliEvaluate:
    def test_evaluate_from_csv(self, tmp_path, capsys):
        csv_path = _make_screen_csv(tmp_path)
        with patch("sys.argv", ["stock-screener", "evaluate", "--input", str(csv_path)]), _patch_provider():
            main()
        captured = capsys.readouterr()
        assert "テスト株A" in captured.out
        assert "テスト株B" in captured.out

    def test_evaluate_prints_verdict(self, tmp_path, capsys):
        csv_path = _make_screen_csv(tmp_path)
        with patch("sys.argv", ["stock-screener", "evaluate", "--input", str(csv_path)]), _patch_provider():
            main()
        captured = capsys.readouterr()
        has_verdict = any(v in captured.out for v in ["INVEST", "REJECT", "WATCHLIST"])
        assert has_verdict

    def test_evaluate_output_csv(self, tmp_path, capsys):
        csv_path = _make_screen_csv(tmp_path)
        output_path = tmp_path / "eval.csv"
        with (
            patch("sys.argv", [
                "stock-screener", "evaluate", "--input", str(csv_path), "--output", str(output_path),
            ]),
            _patch_provider(),
        ):
            main()
        assert output_path.exists()
        with output_path.open() as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == 2
        assert "verdict" in rows[0]
        assert "ticker" in rows[0]
