from stock_screener.market_data.domain.financial_snapshot import FinancialSnapshot
from stock_screener.market_data.domain.security import Security
from stock_screener.shared.types import Ticker


class TestSecurity:
    def test_create(self):
        sec = Security(
            ticker=Ticker("7203"),
            company_name="トヨタ自動車",
            sector="輸送用機器",
            financial_snapshot=FinancialSnapshot(per=10.5, pbr=1.2),
        )
        assert sec.ticker == Ticker("7203")
        assert sec.company_name == "トヨタ自動車"
        assert sec.sector == "輸送用機器"
        assert sec.financial_snapshot.per == 10.5

    def test_create_without_snapshot(self):
        sec = Security(
            ticker=Ticker("6861"),
            company_name="キーエンス",
            sector="電気機器",
        )
        assert sec.financial_snapshot.per is None
