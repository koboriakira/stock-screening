import json
from datetime import date

from stock_screener.monitoring.infrastructure.report_repository import MonitoringReportRepository


def _make_report_data() -> dict:
    return {
        "date": "2026-03-01",
        "results": [
            {
                "ticker": "5599.T",
                "action": "stop_loss",
                "reason": "stop loss triggered",
                "current_price": 1500,
            },
            {
                "ticker": "1234.T",
                "action": "hold",
                "reason": "hold",
                "current_price": 2000,
            },
        ],
    }


class TestMonitoringReportRepository:
    def test_save_creates_json_file(self, tmp_path):
        repo = MonitoringReportRepository(base_dir=tmp_path)
        report = _make_report_data()
        path = repo.save(report, today=date(2026, 3, 1))
        assert path.exists()
        assert path.name == "20260301_monitor.json"

    def test_save_content_is_valid_json(self, tmp_path):
        repo = MonitoringReportRepository(base_dir=tmp_path)
        report = _make_report_data()
        path = repo.save(report, today=date(2026, 3, 1))
        with path.open(encoding="utf-8") as f:
            loaded = json.load(f)
        assert loaded["date"] == "2026-03-01"
        assert len(loaded["results"]) == 2

    def test_save_creates_directory_if_not_exists(self, tmp_path):
        base = tmp_path / "nested" / "dir"
        repo = MonitoringReportRepository(base_dir=base)
        report = _make_report_data()
        path = repo.save(report, today=date(2026, 3, 1))
        assert path.exists()

    def test_default_output_dir(self):
        repo = MonitoringReportRepository()
        assert repo is not None
