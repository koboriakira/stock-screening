from datetime import date

from stock_screener.timing.domain.calendar_schedule import (
    CalendarData,
    DividendInfo,
    EarningsScheduleEntry,
    TickerCalendar,
)
from stock_screener.timing.domain.entry_signal import (
    calc_signal_score,
    check_blockers,
    evaluate_entry,
)
from stock_screener.timing.domain.portfolio import Portfolio


def _make_calendar(
    next_date: str | None = "2026-06-01",
    announced_date: str | None = "2026-02-12",
    is_confirmed: bool = False,
    record_date: str | None = None,
) -> CalendarData:
    return CalendarData(tickers={
        "5599.T": TickerCalendar(
            name="S&J",
            fiscal_year_end="03",
            earnings_schedule=[
                EarningsScheduleEntry(
                    quarter="Q3",
                    announced_date=announced_date,
                    next_date=next_date,
                    is_confirmed=is_confirmed,
                ),
            ],
            dividend=DividendInfo(record_date=record_date, amount_per_share=None),
        ),
    })


def _make_market_data(
    current_price: float = 1780,
    ma25: float = 1800,
    avg_volume_5d: float = 10000,
    is_stop_limit: bool = False,
) -> dict:
    return {
        "current_price": current_price,
        "ma25": ma25,
        "avg_volume_5d": avg_volume_5d,
        "is_stop_limit": is_stop_limit,
    }


class TestCheckBlockers:
    def test_e01_earnings_3_days_before(self):
        """T-E01: B1 決算3営業日前 → wait"""
        # 決算日を today+3 営業日くらいに設定
        result, details = check_blockers(
            "5599.T",
            _make_market_data(),
            _make_calendar(next_date="2026-02-25"),
            today=date(2026, 2, 20),  # 金曜日
        )
        assert result == "wait"
        b1 = next(d for d in details if d["id"] == "B1")
        assert b1["result"] == "FAIL"

    def test_e02_earnings_6_days_before(self):
        """T-E02: B1 決算6営業日前 → pass"""
        _result, details = check_blockers(
            "5599.T",
            _make_market_data(),
            _make_calendar(next_date="2026-03-10"),
            today=date(2026, 2, 20),
        )
        b1 = next(d for d in details if d["id"] == "B1")
        assert b1["result"] == "PASS"

    def test_e03_stop_limit(self):
        """T-E03: B2 ストップ高 → wait"""
        result, details = check_blockers(
            "5599.T",
            _make_market_data(is_stop_limit=True),
            _make_calendar(),
            today=date(2026, 2, 20),
        )
        assert result == "wait"
        b2 = next(d for d in details if d["id"] == "B2")
        assert b2["result"] == "FAIL"

    def test_e04_volume_shortage(self):
        """T-E04: B3 出来高枯渇 → wait"""
        result, details = check_blockers(
            "5599.T",
            _make_market_data(avg_volume_5d=300),
            _make_calendar(),
            today=date(2026, 2, 20),
        )
        assert result == "wait"
        b3 = next(d for d in details if d["id"] == "B3")
        assert b3["result"] == "FAIL"

    def test_all_blockers_pass(self):
        """全ブロッカーPASS"""
        result, details = check_blockers(
            "5599.T",
            _make_market_data(),
            _make_calendar(),
            today=date(2026, 2, 20),
        )
        assert result == "pass"
        assert all(d["result"] == "PASS" for d in details)

    def test_b1_unconfirmed_adds_buffer(self):
        """B1: is_confirmed=false の場合、閾値を +3 営業日に拡張"""
        # EARNINGS_BLACKOUT_DAYS=5, +3=8
        # 7営業日前 → confirmed なら PASS だが unconfirmed なら FAIL
        _result, details = check_blockers(
            "5599.T",
            _make_market_data(),
            _make_calendar(next_date="2026-03-03", is_confirmed=False),
            today=date(2026, 2, 20),
        )
        b1 = next(d for d in details if d["id"] == "B1")
        assert b1["result"] == "FAIL"

    def test_b1_no_calendar_entry(self):
        """カレンダーにティッカーが無い場合 → B1 PASS"""
        empty_cal = CalendarData(tickers={})
        _result, details = check_blockers(
            "5599.T",
            _make_market_data(),
            empty_cal,
            today=date(2026, 2, 20),
        )
        b1 = next(d for d in details if d["id"] == "B1")
        assert b1["result"] == "PASS"


class TestCalcSignalScore:
    def test_e05_s1_below_ma(self):
        """T-E05: S1 MA以下 → +1"""
        _score, details = calc_signal_score(
            "5599.T",
            _make_market_data(current_price=1780, ma25=1800),
            _make_calendar(),
            today=date(2026, 2, 20),
        )
        s1 = next(d for d in details if d["id"] == "S1")
        assert s1["score"] == 1

    def test_e06_s1_above_ma_tolerance(self):
        """T-E06: S1 MAの5%超 → +0"""
        _score, details = calc_signal_score(
            "5599.T",
            _make_market_data(current_price=1900, ma25=1800),
            _make_calendar(),
            today=date(2026, 2, 20),
        )
        s1 = next(d for d in details if d["id"] == "S1")
        assert s1["score"] == 0

    def test_e07_s2_post_earnings_10_days(self):
        """T-E07: S2 決算後10営業日 → +1"""
        # announced_date を today-10営業日くらいに設定
        _score, details = calc_signal_score(
            "5599.T",
            _make_market_data(),
            _make_calendar(announced_date="2026-02-06"),
            today=date(2026, 2, 20),
        )
        s2 = next(d for d in details if d["id"] == "S2")
        assert s2["score"] == 1

    def test_e08_s2_post_earnings_25_days(self):
        """T-E08: S2 決算後25営業日 → +0"""
        _score, details = calc_signal_score(
            "5599.T",
            _make_market_data(),
            _make_calendar(announced_date="2026-01-10"),
            today=date(2026, 2, 20),
        )
        s2 = next(d for d in details if d["id"] == "S2")
        assert s2["score"] == 0

    def test_e09_s5_dividend_45_days(self):
        """T-E09: S5 権利45日前 → +1"""
        _score, details = calc_signal_score(
            "5599.T",
            _make_market_data(),
            _make_calendar(record_date="2026-04-06"),
            today=date(2026, 2, 20),
        )
        s5 = next(d for d in details if d["id"] == "S5")
        assert s5["score"] == 1

    def test_e10_s5_dividend_100_days(self):
        """T-E10: S5 権利100日前 → +0"""
        _score, details = calc_signal_score(
            "5599.T",
            _make_market_data(),
            _make_calendar(record_date="2026-06-01"),
            today=date(2026, 2, 20),
        )
        s5 = next(d for d in details if d["id"] == "S5")
        assert s5["score"] == 0

    def test_s3_always_zero(self):
        """S3 は常に 0 (スケルトン実装)"""
        _score, details = calc_signal_score(
            "5599.T",
            _make_market_data(),
            _make_calendar(),
            today=date(2026, 2, 20),
        )
        s3 = next(d for d in details if d["id"] == "S3")
        assert s3["score"] == 0

    def test_s4_always_zero(self):
        """S4 は常に 0 (スケルトン実装)"""
        _score, details = calc_signal_score(
            "5599.T",
            _make_market_data(),
            _make_calendar(),
            today=date(2026, 2, 20),
        )
        s4 = next(d for d in details if d["id"] == "S4")
        assert s4["score"] == 0


class TestEvaluateEntry:
    def test_e11_score_insufficient(self):
        """T-E11: スコア不足 score=1 → wait"""
        portfolio = Portfolio(total_capital=1_000_000, cash_balance=1_000_000)
        # S1=+1 (1780 <= 1800*1.05), S2=0, S3=0, S4=0, S5=0 → score=1
        result = evaluate_entry(
            "5599.T",
            _make_market_data(current_price=1780, ma25=1800),
            portfolio,
            _make_calendar(announced_date="2025-11-01"),
            today=date(2026, 2, 20),
        )
        assert result["verdict"] == "wait"
        assert result["signal_score"] == 1

    def test_e12_all_pass(self):
        """T-E12: 全条件PASS score>=2 → buy"""
        portfolio = Portfolio(total_capital=1_000_000, cash_balance=1_000_000)
        # S1=+1 (1780 <= 1800*1.05), S2=+1 (announced_date 10日前), S5=+1 (record_date 45日後)
        result = evaluate_entry(
            "5599.T",
            _make_market_data(current_price=1780, ma25=1800),
            portfolio,
            _make_calendar(
                announced_date="2026-02-06",
                record_date="2026-04-06",
            ),
            today=date(2026, 2, 20),
        )
        assert result["verdict"] == "buy"
        assert result["signal_score"] >= 2

    def test_sizing_skip_overrides(self):
        """サイジングskip → verdict=skip"""
        portfolio = Portfolio(total_capital=1_000_000, cash_balance=50_000)
        result = evaluate_entry(
            "5599.T",
            _make_market_data(),
            portfolio,
            _make_calendar(),
            today=date(2026, 2, 20),
        )
        assert result["verdict"] == "skip"

    def test_blocker_wait_overrides(self):
        """ブロッカーwait → verdict=wait"""
        portfolio = Portfolio(total_capital=1_000_000, cash_balance=1_000_000)
        result = evaluate_entry(
            "5599.T",
            _make_market_data(is_stop_limit=True),
            portfolio,
            _make_calendar(),
            today=date(2026, 2, 20),
        )
        assert result["verdict"] == "wait"

    def test_result_structure(self):
        """返却値の構造が正しいこと"""
        portfolio = Portfolio(total_capital=1_000_000, cash_balance=1_000_000)
        result = evaluate_entry(
            "5599.T",
            _make_market_data(),
            portfolio,
            _make_calendar(),
            today=date(2026, 2, 20),
        )
        assert "ticker" in result
        assert "sizing_result" in result
        assert "sizing_message" in result
        assert "blocker_result" in result
        assert "blocker_details" in result
        assert "signal_score" in result
        assert "signal_details" in result
        assert "verdict" in result
        assert "current_price" in result
