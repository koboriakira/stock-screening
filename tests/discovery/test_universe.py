from stock_screener.discovery.domain.universe import Universe
from stock_screener.shared.types import Ticker


class TestUniverse:
    def test_from_jpx_data(self):
        jpx_data = [
            {"ticker": "7203", "company_name": "トヨタ自動車", "sector": "輸送用機器"},
            {"ticker": "6861", "company_name": "キーエンス", "sector": "電気機器"},
        ]
        universe = Universe.from_jpx_data(jpx_data)
        assert len(universe) == 2
        assert universe.securities[0].ticker == Ticker("7203")

    def test_limit(self):
        jpx_data = [
            {"ticker": str(i).zfill(4), "company_name": f"会社{i}", "sector": "電気機器"}
            for i in range(1000, 1010)
        ]
        universe = Universe.from_jpx_data(jpx_data)
        limited = universe.limit(5)
        assert len(limited) == 5
