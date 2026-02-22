"""Tests for config dump function."""

from __future__ import annotations

from stock_screener.shared.config import dump_config


class TestConfigDump:
    def test_dump_returns_string(self):
        result = dump_config()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_dump_includes_market_cap(self):
        result = dump_config()
        assert "market_cap_min" in result
        assert "market_cap_max" in result

    def test_dump_includes_excluded_sectors(self):
        result = dump_config()
        assert "excluded_sectors" in result

    def test_dump_includes_scoring_mode(self):
        result = dump_config()
        assert "scoring_mode" in result

    def test_dump_includes_scoring_weights(self):
        result = dump_config()
        assert "value" in result
        assert "quality" in result
        assert "momentum" in result

    def test_dump_includes_missing_data_policy(self):
        result = dump_config()
        assert "missing_data_policy" in result
