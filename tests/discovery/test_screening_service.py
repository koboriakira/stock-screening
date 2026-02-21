from stock_screener.discovery.domain.candidate import ScreeningResult
from stock_screener.discovery.service import ScreeningService
from stock_screener.market_data.domain.financial_snapshot import FinancialSnapshot
from stock_screener.market_data.domain.security import Security
from stock_screener.shared.types import Ticker


def _make_securities() -> list[Security]:
    """テスト用の混合銘柄セット"""
    return [
        # 小型割安: ハード/ソフト通過、高スコア
        Security(
            ticker=Ticker("1001"),
            company_name="割安小型A",
            sector="電気機器",
            financial_snapshot=FinancialSnapshot(
                market_cap=10_000_000_000,
                avg_trading_value=50_000_000,
                per=8.0,
                pbr=0.6,
                roe=0.10,
                operating_margin=0.08,
                equity_ratio=0.50,
                revenue_growth=0.15,
                dividend_yield=0.03,
                high_52w_discount=0.20,
                net_cash_ratio=0.30,
            ),
        ),
        # 小型割安: ハード/ソフト通過、中スコア
        Security(
            ticker=Ticker("1002"),
            company_name="割安小型B",
            sector="機械",
            financial_snapshot=FinancialSnapshot(
                market_cap=20_000_000_000,
                avg_trading_value=30_000_000,
                per=12.0,
                pbr=1.0,
                roe=0.06,
                operating_margin=0.05,
                equity_ratio=0.35,
                revenue_growth=0.05,
                dividend_yield=0.02,
                high_52w_discount=0.10,
                net_cash_ratio=0.10,
            ),
        ),
        # 大型: ハードフィルタで除外 (時価総額オーバー)
        Security(
            ticker=Ticker("1003"),
            company_name="大型株",
            sector="電気機器",
            financial_snapshot=FinancialSnapshot(
                market_cap=100_000_000_000,
                avg_trading_value=500_000_000,
                per=15.0,
                pbr=2.0,
            ),
        ),
        # 医薬品: セクター除外
        Security(
            ticker=Ticker("1004"),
            company_name="バイオ株",
            sector="医薬品",
            financial_snapshot=FinancialSnapshot(
                market_cap=8_000_000_000,
                avg_trading_value=20_000_000,
            ),
        ),
        # PER高すぎ: ソフトフィルタで除外
        Security(
            ticker=Ticker("1005"),
            company_name="高PER株",
            sector="情報・通信業",
            financial_snapshot=FinancialSnapshot(
                market_cap=15_000_000_000,
                avg_trading_value=40_000_000,
                per=80.0,
                pbr=5.0,
            ),
        ),
    ]


class TestScreeningService:
    def test_full_pipeline(self):
        securities = _make_securities()
        service = ScreeningService()
        result = service.execute(securities, top_n=10)

        assert isinstance(result, ScreeningResult)
        assert result.total_universe == 5
        assert result.after_hard_filter == 3  # 大型 + 医薬品 が除外
        assert result.after_soft_filter == 2  # 高PER が除外
        assert len(result.candidates) == 2

    def test_ranking_order(self):
        securities = _make_securities()
        service = ScreeningService()
        result = service.execute(securities, top_n=10)

        # 割安小型A (1001) の方がスコアが高いはず
        assert result.candidates[0].security.ticker == Ticker("1001")
        assert result.candidates[0].rank == 1
        assert result.candidates[1].rank == 2
        assert result.candidates[0].score.total >= result.candidates[1].score.total

    def test_top_n_limit(self):
        securities = _make_securities()
        service = ScreeningService()
        result = service.execute(securities, top_n=1)
        assert len(result.candidates) == 1

    def test_empty_universe(self):
        service = ScreeningService()
        result = service.execute([], top_n=10)
        assert len(result.candidates) == 0
        assert result.total_universe == 0
