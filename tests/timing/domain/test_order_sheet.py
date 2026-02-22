import json
from datetime import date

from stock_screener.timing.domain.order_sheet import generate_order_sheet
from stock_screener.timing.domain.portfolio import Holding, Portfolio


def _make_entry_results():
    return [
        {
            "ticker": "5599.T",
            "sizing_result": "pass",
            "sizing_message": "OK",
            "blocker_result": "pass",
            "blocker_details": [
                {"id": "B1", "result": "PASS", "message": "OK"},
                {"id": "B2", "result": "PASS", "message": "OK"},
                {"id": "B3", "result": "PASS", "message": "OK"},
            ],
            "signal_score": 3,
            "signal_details": [
                {"id": "S1", "score": 1, "message": "OK"},
                {"id": "S2", "score": 1, "message": "OK"},
                {"id": "S5", "score": 1, "message": "OK"},
            ],
            "verdict": "buy",
            "current_price": 1780,
        },
        {
            "ticker": "4486.T",
            "sizing_result": "pass",
            "sizing_message": "OK",
            "blocker_result": "pass",
            "blocker_details": [],
            "signal_score": 1,
            "signal_details": [],
            "verdict": "wait",
            "current_price": 1200,
        },
    ]


def _make_exit_results():
    return [
        {
            "ticker": "4440.T",
            "action": "stop_loss",
            "reason": "損切り",
            "current_price": 800,
            "unrealized_pnl": -20000,
            "unrealized_pnl_pct": -0.20,
        },
    ]


def _make_portfolio():
    return Portfolio(
        total_capital=1_000_000,
        cash_balance=1_000_000,
        holdings=[
            Holding(
                ticker="4440.T",
                name="ヴィッツ",
                shares=100,
                entry_price=1000,
                entry_date=date(2025, 10, 1),
                stop_loss=850,
                target_price=1500,
                max_holding_date=date(2026, 3, 30),
            ),
        ],
    )


class TestGenerateOrderSheet:
    def test_generates_text_output(self):
        """テキスト出力が生成されること"""
        text = generate_order_sheet(
            _make_entry_results(),
            _make_exit_results(),
            _make_portfolio(),
            today=date(2026, 2, 22),
        )
        assert "5599.T" in text
        assert "buy" in text.lower()
        assert "4486.T" in text
        assert "wait" in text.lower()
        assert "4440.T" in text
        assert "stop_loss" in text.lower()

    def test_generates_json_output(self, tmp_path):
        """JSONファイルが正しいスキーマで生成されること"""
        generate_order_sheet(
            _make_entry_results(),
            _make_exit_results(),
            _make_portfolio(),
            today=date(2026, 2, 22),
            output_dir=str(tmp_path),
        )
        json_path = tmp_path / "20260222_order.json"
        assert json_path.exists()

        with json_path.open() as f:
            data = json.load(f)

        assert data["date"] == "2026-02-22"
        assert data["total_capital"] == 1_000_000
        assert data["cash_balance"] == 1_000_000
        assert len(data["entry_results"]) == 2
        assert len(data["exit_results"]) == 1
        assert "summary" in data

    def test_summary_counts(self, tmp_path):
        """サマリーのカウントが正しいこと"""
        generate_order_sheet(
            _make_entry_results(),
            _make_exit_results(),
            _make_portfolio(),
            today=date(2026, 2, 22),
            output_dir=str(tmp_path),
        )
        json_path = tmp_path / "20260222_order.json"
        with json_path.open() as f:
            data = json.load(f)

        summary = data["summary"]
        assert summary["buy_count"] == 1
        assert summary["wait_count"] == 1
        assert summary["skip_count"] == 0

    def test_empty_results(self, tmp_path):
        """空の結果でもエラーなく動作すること"""
        portfolio = Portfolio(total_capital=1_000_000, cash_balance=1_000_000)
        text = generate_order_sheet(
            [],
            [],
            portfolio,
            today=date(2026, 2, 22),
            output_dir=str(tmp_path),
        )
        assert "2026-02-22" in text
