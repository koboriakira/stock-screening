from stock_screener.timing.domain.config import (
    DIVIDEND_RECORD_MAX_DAYS,
    DIVIDEND_RECORD_MIN_DAYS,
    EARNINGS_BLACKOUT_DAYS,
    EXTENSION_DAYS,
    LOT_SIZE,
    MA_PERIOD,
    MA_TOLERANCE,
    MAX_CONCENTRATION,
    MAX_HOLDING_DAYS,
    MIN_AVG_VOLUME_5D,
    MIN_CASH_RESERVE,
    POST_EARNINGS_MAX_DAYS,
    POST_EARNINGS_MIN_DAYS,
    SIGNAL_THRESHOLD,
    STOP_LOSS_PCT,
    TARGET_GAIN_PCT,
    TRAILING_STEP_PCT,
)


class TestTimingConfig:
    def test_lot_size_is_100(self):
        assert LOT_SIZE == 100

    def test_max_concentration_is_050(self):
        assert MAX_CONCENTRATION == 0.50

    def test_min_cash_reserve_is_010(self):
        assert MIN_CASH_RESERVE == 0.10

    def test_earnings_blackout_days_is_5(self):
        assert EARNINGS_BLACKOUT_DAYS == 5

    def test_min_avg_volume_5d_is_500(self):
        assert MIN_AVG_VOLUME_5D == 500

    def test_signal_threshold_is_2(self):
        assert SIGNAL_THRESHOLD == 2

    def test_ma_period_is_25(self):
        assert MA_PERIOD == 25

    def test_ma_tolerance_is_105(self):
        assert MA_TOLERANCE == 1.05

    def test_post_earnings_min_days_is_3(self):
        assert POST_EARNINGS_MIN_DAYS == 3

    def test_post_earnings_max_days_is_20(self):
        assert POST_EARNINGS_MAX_DAYS == 20

    def test_dividend_record_min_days_is_30(self):
        assert DIVIDEND_RECORD_MIN_DAYS == 30

    def test_dividend_record_max_days_is_90(self):
        assert DIVIDEND_RECORD_MAX_DAYS == 90

    def test_stop_loss_pct_is_015(self):
        assert STOP_LOSS_PCT == 0.15

    def test_target_gain_pct_is_050(self):
        assert TARGET_GAIN_PCT == 0.50

    def test_trailing_step_pct_is_025(self):
        assert TRAILING_STEP_PCT == 0.25

    def test_max_holding_days_is_180(self):
        assert MAX_HOLDING_DAYS == 180

    def test_extension_days_is_90(self):
        assert EXTENSION_DAYS == 90

    def test_all_constants_are_correct_types(self):
        assert isinstance(LOT_SIZE, int)
        assert isinstance(EARNINGS_BLACKOUT_DAYS, int)
        assert isinstance(MIN_AVG_VOLUME_5D, int)
        assert isinstance(SIGNAL_THRESHOLD, int)
        assert isinstance(MA_PERIOD, int)
        assert isinstance(POST_EARNINGS_MIN_DAYS, int)
        assert isinstance(POST_EARNINGS_MAX_DAYS, int)
        assert isinstance(DIVIDEND_RECORD_MIN_DAYS, int)
        assert isinstance(DIVIDEND_RECORD_MAX_DAYS, int)
        assert isinstance(MAX_HOLDING_DAYS, int)
        assert isinstance(EXTENSION_DAYS, int)
        assert isinstance(MAX_CONCENTRATION, float)
        assert isinstance(MIN_CASH_RESERVE, float)
        assert isinstance(MA_TOLERANCE, float)
        assert isinstance(STOP_LOSS_PCT, float)
        assert isinstance(TARGET_GAIN_PCT, float)
        assert isinstance(TRAILING_STEP_PCT, float)
