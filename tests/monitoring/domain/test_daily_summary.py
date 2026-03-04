from datetime import date

from stock_screener.monitoring.domain.bottom_detector import BottomSignal
from stock_screener.monitoring.domain.daily_summary import format_daily_summary


class TestFormatDailySummary:
    def test_header_contains_date(self):
        today = date(2026, 3, 4)
        result = format_daily_summary(
            monitor_results=[], watchlist_results=[], today=today, analysis_alerts=[],
        )
        assert "[日次モニタリング 03/04]" in result

    def test_portfolio_section_with_holding(self):
        today = date(2026, 3, 4)
        monitor_results = [
            {
                "ticker": "4486.T",
                "name": "ユニティ",
                "action": "hold",
                "current_price": 657.0,
                "entry_price": 675.0,
                "unrealized_pnl_pct": -0.027,
                "days_held": 7,
                "max_holding_date": "2026-03-27",
                "stop_loss": 648.0,
                "target_price": 877.5,
            },
        ]
        result = format_daily_summary(
            monitor_results=monitor_results,
            watchlist_results=[],
            today=today,
            analysis_alerts=[],
        )
        assert "■ 保有銘柄" in result
        assert "4486.T" in result
        assert "ユニティ" in result
        assert "hold" in result
        assert "657" in result
        assert "675" in result
        assert "-2.7%" in result

    def test_portfolio_section_empty(self):
        today = date(2026, 3, 4)
        result = format_daily_summary(
            monitor_results=[], watchlist_results=[], today=today, analysis_alerts=[],
        )
        assert "■ 保有銘柄" in result
        assert "対象なし" in result

    def test_watchlist_section_with_entry(self):
        today = date(2026, 3, 4)
        signal = BottomSignal(
            ticker="5599.T", score=1, max_score=5, level=None,
            rsi_signal=False, bb_signal=False, macd_signal=False,
            volume_confirmed=False, ma_crossover=True,
            details={"rsi": 28.5, "volume_ratio": 0.8},
            score_delta=1,
        )
        watchlist_results = [
            {
                "ticker": "5599.T",
                "name": "S&J",
                "signal": signal,
                "current_price": 1508.0,
                "registered_price": 1780.0,
                "price_change_pct": -0.153,
                "score_change_reasons": ["MA点灯"],
            },
        ]
        result = format_daily_summary(
            monitor_results=[],
            watchlist_results=watchlist_results,
            today=today,
            analysis_alerts=[],
        )
        assert "■ ウォッチリスト" in result
        assert "5599.T" in result
        assert "S&J" in result
        assert "1,508" in result
        assert "-15.3%" in result
        assert "1/5" in result
        assert "+1" in result
        assert "RSI:x" in result
        assert "MA:o" in result
        assert "MA点灯" in result

    def test_watchlist_section_empty(self):
        today = date(2026, 3, 4)
        result = format_daily_summary(
            monitor_results=[], watchlist_results=[], today=today, analysis_alerts=[],
        )
        assert "■ ウォッチリスト" in result
        assert "対象なし" in result

    def test_analysis_alerts_section(self):
        today = date(2026, 3, 4)
        alerts = [
            {
                "type": "support_approach",
                "ticker": "4486.T",
                "level": {"price": 640, "label": "直近安値"},
            },
            {
                "type": "key_date_approaching",
                "ticker": "4486.T",
                "event": "決算発表",
                "severity": "high",
            },
        ]
        result = format_daily_summary(
            monitor_results=[], watchlist_results=[], today=today,
            analysis_alerts=alerts,
        )
        assert "■ 分析アラート" in result
        assert "サポート接近" in result
        assert "640" in result
        assert "決算発表" in result

    def test_no_analysis_alerts_section_when_empty(self):
        today = date(2026, 3, 4)
        result = format_daily_summary(
            monitor_results=[], watchlist_results=[], today=today, analysis_alerts=[],
        )
        assert "■ 分析アラート" not in result

    def test_holding_days_remaining(self):
        today = date(2026, 3, 4)
        monitor_results = [
            {
                "ticker": "4486.T",
                "name": "ユニティ",
                "action": "hold",
                "current_price": 657.0,
                "entry_price": 675.0,
                "unrealized_pnl_pct": -0.027,
                "days_held": 7,
                "max_holding_date": "2026-03-27",
                "stop_loss": 648.0,
                "target_price": 877.5,
            },
        ]
        result = format_daily_summary(
            monitor_results=monitor_results,
            watchlist_results=[],
            today=today,
            analysis_alerts=[],
        )
        assert "保有7日" in result
        assert "残23日" in result

    def test_stop_loss_and_target_distance(self):
        today = date(2026, 3, 4)
        monitor_results = [
            {
                "ticker": "4486.T",
                "name": "ユニティ",
                "action": "hold",
                "current_price": 675.0,
                "entry_price": 675.0,
                "unrealized_pnl_pct": 0.0,
                "days_held": 1,
                "max_holding_date": "2026-04-03",
                "stop_loss": 648.0,
                "target_price": 877.5,
            },
        ]
        result = format_daily_summary(
            monitor_results=monitor_results,
            watchlist_results=[],
            today=today,
            analysis_alerts=[],
        )
        assert "損切りまで-4.0%" in result
        assert "利確まで+30.0%" in result

    def test_watchlist_signal_details(self):
        """RSI値と出来高比がサマリーに含まれる"""
        today = date(2026, 3, 4)
        signal = BottomSignal(
            ticker="4440.T", score=0, max_score=5, level=None,
            rsi_signal=False, bb_signal=False, macd_signal=False,
            volume_confirmed=False, ma_crossover=False,
            details={"rsi": 45.2, "volume_ratio": 0.6},
            score_delta=0,
        )
        watchlist_results = [
            {
                "ticker": "4440.T",
                "name": "ヴィッツ",
                "signal": signal,
                "current_price": 1394.0,
                "registered_price": 1435.0,
                "price_change_pct": -0.029,
                "score_change_reasons": [],
            },
        ]
        result = format_daily_summary(
            monitor_results=[],
            watchlist_results=watchlist_results,
            today=today,
            analysis_alerts=[],
        )
        assert "RSI:45.2" in result
        assert "出来高比:0.6" in result
