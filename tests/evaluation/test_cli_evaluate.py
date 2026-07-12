from __future__ import annotations

import csv
import json
from unittest.mock import patch

import pytest

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
    """CLIが_build_eval_providerで外部APIを呼ぶのを防ぐモック。"""
    return patch(
        "stock_screener.cli._build_eval_provider",
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

    def test_evaluate_shows_needs_review_count(self, tmp_path, capsys):
        """評価出力にNEEDS_REVIEW項目数が表示される。"""
        csv_path = _make_screen_csv(tmp_path)
        with patch("sys.argv", ["stock-screener", "evaluate", "--input", str(csv_path)]), _patch_provider():
            main()
        captured = capsys.readouterr()
        # 各Gateの要確認数が表示されること
        assert "?" in captured.out

    def test_evaluate_shows_check_ids(self, tmp_path, capsys):
        """評価出力に check_id が表示される。"""
        csv_path = _make_screen_csv(tmp_path)
        with patch("sys.argv", ["stock-screener", "evaluate", "--input", str(csv_path)]), _patch_provider():
            main()
        captured = capsys.readouterr()
        # Gate1 のチェックIDが表示されること
        assert "1-1" in captured.out
        assert "1-2" in captured.out

    def test_evaluate_summary_shows_gate_stats(self, tmp_path, capsys):
        """一覧表にGateの統計情報(PASS/FAIL/要確認数)が表示される。"""
        csv_path = _make_screen_csv(tmp_path)
        with patch("sys.argv", ["stock-screener", "evaluate", "--input", str(csv_path)]), _patch_provider():
            main()
        captured = capsys.readouterr()
        # Gate詳細にNEEDS_REVIEW数が含まれること
        assert "要確認" in captured.out

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

    def test_evaluate_output_detail_csv(self, tmp_path, capsys):
        """--output 指定時に _detail サフィックス付きの詳細CSVも生成される。"""
        csv_path = _make_screen_csv(tmp_path)
        output_path = tmp_path / "eval.csv"
        detail_path = tmp_path / "eval_detail.csv"
        with (
            patch("sys.argv", [
                "stock-screener", "evaluate", "--input", str(csv_path), "--output", str(output_path),
            ]),
            _patch_provider(),
        ):
            main()
        assert detail_path.exists()

    def test_detail_csv_has_expected_columns(self, tmp_path, capsys):
        """詳細CSVに必要なカラムが全て含まれている。"""
        csv_path = _make_screen_csv(tmp_path)
        output_path = tmp_path / "eval.csv"
        detail_path = tmp_path / "eval_detail.csv"
        with (
            patch("sys.argv", [
                "stock-screener", "evaluate", "--input", str(csv_path), "--output", str(output_path),
            ]),
            _patch_provider(),
        ):
            main()
        with detail_path.open() as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        expected_cols = {
            "rank", "ticker", "company_name", "sector", "verdict", "score_total",
            "gate", "check_id", "check_status", "check_description", "check_detail",
        }
        assert expected_cols == set(rows[0].keys())

    def test_detail_csv_has_all_checks_per_stock(self, tmp_path, capsys):
        """詳細CSVが銘柄数 x チェック項目数の行数を持つ(縦展開)。"""
        csv_path = _make_screen_csv(tmp_path)
        output_path = tmp_path / "eval.csv"
        detail_path = tmp_path / "eval_detail.csv"
        with (
            patch("sys.argv", [
                "stock-screener", "evaluate", "--input", str(csv_path), "--output", str(output_path),
            ]),
            _patch_provider(),
        ):
            main()
        with detail_path.open() as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        # 2銘柄 x 18チェック = 36行
        assert len(rows) == 36
        # 各銘柄のcheck_idが18個ずつ
        stock_a_rows = [r for r in rows if r["ticker"] == "1001.T"]
        stock_b_rows = [r for r in rows if r["ticker"] == "1002.T"]
        assert len(stock_a_rows) == 18
        assert len(stock_b_rows) == 18

    def test_detail_csv_contains_gate_info(self, tmp_path, capsys):
        """詳細CSVの各行にGate情報が含まれている。"""
        csv_path = _make_screen_csv(tmp_path)
        output_path = tmp_path / "eval.csv"
        detail_path = tmp_path / "eval_detail.csv"
        with (
            patch("sys.argv", [
                "stock-screener", "evaluate", "--input", str(csv_path), "--output", str(output_path),
            ]),
            _patch_provider(),
        ):
            main()
        with detail_path.open() as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        gates_in_csv = {r["gate"] for r in rows}
        assert "Gate1" in gates_in_csv or any("Gate1" in g for g in gates_in_csv)
        check_ids_in_csv = {r["check_id"] for r in rows}
        assert "1-1" in check_ids_in_csv
        assert "2A-2" in check_ids_in_csv
        assert "3-2" in check_ids_in_csv


class TestEvaluateJsonFormat:
    def test_default_format_is_table(self, tmp_path, capsys):
        """--format 省略時は table 形式のまま (既存挙動を破壊しない)。"""
        csv_path = _make_screen_csv(tmp_path)
        with patch("sys.argv", ["stock-screener", "evaluate", "--input", str(csv_path)]), _patch_provider():
            main()
        captured = capsys.readouterr()
        assert "評価結果" in captured.out
        with pytest.raises(json.JSONDecodeError):
            json.loads(captured.out)

    def test_evaluate_json_single_object(self, tmp_path, capsys):
        """--format json 指定時、stdout は JSON 1オブジェクトのみ。"""
        csv_path = _make_screen_csv(tmp_path)
        with (
            patch("sys.argv", ["stock-screener", "evaluate", "--input", str(csv_path), "--format", "json"]),
            _patch_provider(),
        ):
            main()
        out = capsys.readouterr().out.strip()
        payload = json.loads(out)  # パースできること自体が「1オブジェクトのみ」の検証になる
        assert payload["type"] == "evaluate"
        assert payload["source"] == "yfinance"
        assert payload["count"] == 2

    def test_evaluate_json_item_shape(self, tmp_path, capsys):
        """item は rank/ticker/company_name/verdict/verdict_reason/score_total/gates を含む。"""
        csv_path = _make_screen_csv(tmp_path)
        with (
            patch("sys.argv", ["stock-screener", "evaluate", "--input", str(csv_path), "--format", "json"]),
            _patch_provider(),
        ):
            main()
        payload = json.loads(capsys.readouterr().out)
        item = payload["items"][0]
        for f in ["rank", "ticker", "company_name", "verdict", "verdict_reason", "score_total", "gates"]:
            assert f in item, f"Missing field: {f}"
        assert item["verdict"] in {"INVEST", "WATCHLIST", "REJECT"}
        assert len(item["gates"]) == 3
        gate_names = [g["name"] for g in item["gates"]]
        assert gate_names == ["gate1", "gate2", "gate3"]
        for gate in item["gates"]:
            assert "passed" in gate
            assert "checks" in gate
            for check in gate["checks"]:
                assert {"id", "status", "description", "detail"} <= set(check.keys())

    def test_evaluate_json_needs_review_status_present(self, tmp_path, capsys):
        """StubEvaluationDataProvider 使用時、NEEDS_REVIEW がチェックの status 値として現れる (エラーにしない)。"""
        csv_path = _make_screen_csv(tmp_path)
        with (
            patch("sys.argv", ["stock-screener", "evaluate", "--input", str(csv_path), "--format", "json"]),
            _patch_provider(),
        ):
            main()
        payload = json.loads(capsys.readouterr().out)
        all_statuses = {
            check["status"] for item in payload["items"] for gate in item["gates"] for check in gate["checks"]
        }
        assert "NEEDS_REVIEW" in all_statuses

    def test_evaluate_json_still_writes_csv(self, tmp_path):
        """json モードでも --output の CSV (本体 + detail) は維持される。"""
        csv_path = _make_screen_csv(tmp_path)
        output_path = tmp_path / "eval.csv"
        detail_path = tmp_path / "eval_detail.csv"
        with (
            patch(
                "sys.argv",
                [
                    "stock-screener",
                    "evaluate",
                    "--input",
                    str(csv_path),
                    "--output",
                    str(output_path),
                    "--format",
                    "json",
                ],
            ),
            _patch_provider(),
        ):
            main()
        assert output_path.exists()
        assert detail_path.exists()

    def test_evaluate_json_missing_input_file_returns_error(self, tmp_path, capsys):
        """json モードで入力ファイル不在 -> type:error + exit 2。"""
        missing_path = tmp_path / "does_not_exist.csv"
        with (
            patch("sys.argv", ["stock-screener", "evaluate", "--input", str(missing_path), "--format", "json"]),
            _patch_provider(),
            pytest.raises(SystemExit) as exc_info,
        ):
            main()
        assert exc_info.value.code == 2
        out = json.loads(capsys.readouterr().out)
        assert out["type"] == "error"
