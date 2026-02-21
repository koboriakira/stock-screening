import pytest

from stock_screener.discovery.domain.scoring import CompositeScorer
from stock_screener.discovery.domain.scoring.momentum_score import MomentumScorer
from stock_screener.discovery.domain.scoring.quality_score import QualityScorer
from stock_screener.discovery.domain.scoring.value_score import ValueScorer
from stock_screener.market_data.domain.financial_snapshot import FinancialSnapshot


class TestValueScorer:
    """仕様: PER 0-25, PBR 0-25, ネットキャッシュ比率 0-25, 52週高値乖離率 0-25"""

    def test_per_very_low(self):
        assert ValueScorer.score_per(5.0) == 25

    def test_per_low(self):
        score = ValueScorer.score_per(10.0)
        assert 0 < score < 25

    def test_per_mid(self):
        score = ValueScorer.score_per(15.0)
        # 線形補間: (15-5)/(30-5) = 10/25 => 25 - 25*(10/25) = 15.0
        assert score == pytest.approx(15.0)

    def test_per_high(self):
        assert ValueScorer.score_per(30.0) == 0

    def test_per_none(self):
        assert ValueScorer.score_per(None) == 0

    def test_pbr_very_low(self):
        assert ValueScorer.score_pbr(0.5) == 25

    def test_pbr_at_1(self):
        # 線形補間: (1.0-0.5)/(2.0-0.5) = 0.5/1.5 => 25 - 25*(1/3) = 16.67
        assert ValueScorer.score_pbr(1.0) == pytest.approx(16.67, abs=0.01)

    def test_pbr_high(self):
        assert ValueScorer.score_pbr(2.0) == 0

    def test_pbr_none(self):
        assert ValueScorer.score_pbr(None) == 0

    def test_net_cash_ratio_high(self):
        assert ValueScorer.score_net_cash_ratio(0.50) == 25

    def test_net_cash_ratio_zero(self):
        assert ValueScorer.score_net_cash_ratio(0.0) == 5

    def test_net_cash_ratio_none(self):
        assert ValueScorer.score_net_cash_ratio(None) == 0

    def test_52w_discount_deep(self):
        # 30%以上下落 = 25点
        assert ValueScorer.score_52w_discount(0.30) == 25

    def test_52w_discount_moderate(self):
        # 線形補間: 0.10/0.30 * 25 = 8.33
        score = ValueScorer.score_52w_discount(0.10)
        assert score == pytest.approx(8.33, abs=0.01)

    def test_52w_discount_at_high(self):
        # 高値圏 = 0点
        assert ValueScorer.score_52w_discount(0.0) == 0

    def test_52w_discount_none(self):
        assert ValueScorer.score_52w_discount(None) == 0

    def test_total_value_score(self):
        snap = FinancialSnapshot(per=5.0, pbr=0.5, net_cash_ratio=0.5, high_52w_discount=0.3)
        score = ValueScorer.score(snap)
        assert score == 100  # all max


class TestQualityScorer:
    """仕様: ROE 0-35, 営業利益率 0-35, 自己資本比率 0-30"""

    def test_roe_high(self):
        assert QualityScorer.score_roe(0.08) == 35

    def test_roe_mid(self):
        # 線形補間: 0.05/0.08 * 35 = 21.875
        score = QualityScorer.score_roe(0.05)
        assert score == pytest.approx(21.875)

    def test_roe_zero(self):
        assert QualityScorer.score_roe(0.0) == 0

    def test_roe_none(self):
        assert QualityScorer.score_roe(None) == 0

    def test_operating_margin_high(self):
        assert QualityScorer.score_operating_margin(0.10) == 35

    def test_operating_margin_mid(self):
        # 線形補間: 0.05/0.10 * 35 = 17.5
        assert QualityScorer.score_operating_margin(0.05) == pytest.approx(17.5)

    def test_operating_margin_zero(self):
        assert QualityScorer.score_operating_margin(0.0) == 0

    def test_operating_margin_none(self):
        assert QualityScorer.score_operating_margin(None) == 0

    def test_equity_ratio_high(self):
        assert QualityScorer.score_equity_ratio(0.50) == 30

    def test_equity_ratio_mid(self):
        assert QualityScorer.score_equity_ratio(0.30) == 15

    def test_equity_ratio_low(self):
        assert QualityScorer.score_equity_ratio(0.20) == 5

    def test_equity_ratio_none(self):
        assert QualityScorer.score_equity_ratio(None) == 0

    def test_total_quality_score(self):
        snap = FinancialSnapshot(roe=0.08, operating_margin=0.10, equity_ratio=0.50)
        score = QualityScorer.score(snap)
        assert score == 100  # all max


class TestMomentumScorer:
    """仕様: 売上高成長率 0-35, 営業利益成長率 0-35, 配当利回り変化 0-30"""

    def test_revenue_growth_high(self):
        assert MomentumScorer.score_revenue_growth(0.20) == 35

    def test_revenue_growth_moderate(self):
        # 線形補間: 10 + (0.10/0.20)*(35-10) = 22.5
        assert MomentumScorer.score_revenue_growth(0.10) == pytest.approx(22.5)

    def test_revenue_growth_flat(self):
        assert MomentumScorer.score_revenue_growth(0.0) == 10

    def test_revenue_growth_negative(self):
        assert MomentumScorer.score_revenue_growth(-0.05) == 0

    def test_revenue_growth_none(self):
        assert MomentumScorer.score_revenue_growth(None) == 0

    def test_op_growth_high(self):
        assert MomentumScorer.score_operating_profit_growth(0.30) == 35

    def test_op_growth_moderate(self):
        # 線形補間: 5 + (0.10/0.30)*(35-5) = 15.0
        assert MomentumScorer.score_operating_profit_growth(0.10) == pytest.approx(15.0)

    def test_op_growth_flat(self):
        assert MomentumScorer.score_operating_profit_growth(0.0) == 5

    def test_op_growth_none(self):
        assert MomentumScorer.score_operating_profit_growth(None) == 0

    def test_dividend_yield_good(self):
        # 配当利回りがある = 高スコア (簡易: 利回り自体をスコア化)
        score = MomentumScorer.score_dividend_yield(0.04)
        assert score > 0

    def test_dividend_yield_none(self):
        assert MomentumScorer.score_dividend_yield(None) == 0


class TestCompositeScorer:
    def test_weighted_score(self):
        snap = FinancialSnapshot(
            per=5.0,
            pbr=0.5,
            net_cash_ratio=0.5,
            high_52w_discount=0.3,
            roe=0.08,
            operating_margin=0.10,
            equity_ratio=0.50,
            revenue_growth=0.20,
            operating_profit_growth=0.30,
            dividend_yield=0.04,
        )
        result = CompositeScorer.score(snap)
        # All max: value=100*0.4 + quality=100*0.3 + momentum=100*0.3 = 100
        assert result.total == 100

    def test_all_none(self):
        snap = FinancialSnapshot()
        result = CompositeScorer.score(snap)
        assert result.total == 0

    def test_turnaround_bonus(self):
        snap = FinancialSnapshot(
            per=10.0,
            operating_profit_growth=0.30,
        )
        result_no_turnaround = CompositeScorer.score(snap, prev_operating_profit_negative=False)
        result_turnaround = CompositeScorer.score(snap, prev_operating_profit_negative=True)
        assert result_turnaround.total == result_no_turnaround.total + 10

    def test_score_capped_at_100(self):
        snap = FinancialSnapshot(
            per=5.0, pbr=0.5, net_cash_ratio=0.5, high_52w_discount=0.3,
            roe=0.08, operating_margin=0.10, equity_ratio=0.50,
            revenue_growth=0.20, operating_profit_growth=0.30, dividend_yield=0.04,
        )
        result = CompositeScorer.score(snap, prev_operating_profit_negative=True)
        assert result.total <= 100
