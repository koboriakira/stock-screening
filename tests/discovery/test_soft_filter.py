from stock_screener.discovery.domain.soft_filter import SoftFilter
from stock_screener.market_data.domain.financial_snapshot import FinancialSnapshot
from stock_screener.market_data.domain.security import Security
from stock_screener.shared.types import Ticker


def _make_security(
    per: float | None = 15.0,
    equity_ratio: float | None = 0.40,
    revenue_growth: float | None = 0.05,
) -> Security:
    return Security(
        ticker=Ticker("1234"),
        company_name="テスト株式会社",
        sector="電気機器",
        financial_snapshot=FinancialSnapshot(
            per=per,
            equity_ratio=equity_ratio,
            revenue_growth=revenue_growth,
        ),
    )


class TestSoftFilter:
    def test_passes_valid_security(self):
        result = SoftFilter().apply([_make_security()])
        assert len(result) == 1

    def test_excludes_high_per(self):
        result = SoftFilter().apply([_make_security(per=55.0)])
        assert len(result) == 0

    def test_excludes_negative_per(self):
        result = SoftFilter().apply([_make_security(per=-5.0)])
        assert len(result) == 0

    def test_excludes_low_equity_ratio(self):
        result = SoftFilter().apply([_make_security(equity_ratio=0.15)])
        assert len(result) == 0

    def test_excludes_severe_revenue_decline(self):
        result = SoftFilter().apply([_make_security(revenue_growth=-0.35)])
        assert len(result) == 0

    def test_none_per_passes(self):
        result = SoftFilter().apply([_make_security(per=None)])
        assert len(result) == 1

    def test_none_equity_ratio_passes(self):
        result = SoftFilter().apply([_make_security(equity_ratio=None)])
        assert len(result) == 1

    def test_none_revenue_growth_passes(self):
        result = SoftFilter().apply([_make_security(revenue_growth=None)])
        assert len(result) == 1

    def test_boundary_per_max(self):
        result = SoftFilter().apply([_make_security(per=50.0)])
        assert len(result) == 1

    def test_boundary_equity_ratio_min(self):
        result = SoftFilter().apply([_make_security(equity_ratio=0.20)])
        assert len(result) == 1

    def test_boundary_revenue_growth_min(self):
        result = SoftFilter().apply([_make_security(revenue_growth=-0.30)])
        assert len(result) == 1
