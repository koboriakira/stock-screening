from unittest.mock import patch

import pandas as pd

from stock_screener.market_data.infrastructure.jpx_stock_list import JpxStockListFetcher


def _create_mock_jpx_df() -> pd.DataFrame:
    return pd.DataFrame({
        "コード": [7203, 6861, 6758, 4502, 3462],
        "銘柄名": ["トヨタ自動車", "キーエンス", "ソニーG", "武田薬品工業", "ライフル"],
        "市場・商品区分": [
            "プライム（内国株式）",
            "プライム（内国株式）",
            "プライム（内国株式）",
            "プライム（内国株式）",
            "グロース（内国株式）",
        ],
        "33業種区分": ["輸送用機器", "電気機器", "電気機器", "医薬品", "不動産業"],
    })


class TestJpxStockListFetcher:
    def test_fetch_returns_securities(self):
        mock_df = _create_mock_jpx_df()
        fetcher = JpxStockListFetcher()

        with patch("pandas.read_excel", return_value=mock_df):
            result = fetcher.fetch()

        assert len(result) == 5
        assert result[0]["ticker"] == "7203"
        assert result[0]["company_name"] == "トヨタ自動車"
        assert result[0]["sector"] == "輸送用機器"

    def test_fetch_parses_market(self):
        mock_df = _create_mock_jpx_df()
        fetcher = JpxStockListFetcher()

        with patch("pandas.read_excel", return_value=mock_df):
            result = fetcher.fetch()

        assert result[0]["market"] == "プライム"
        assert result[4]["market"] == "グロース"

    def test_fetch_converts_ticker_to_string(self):
        mock_df = _create_mock_jpx_df()
        fetcher = JpxStockListFetcher()

        with patch("pandas.read_excel", return_value=mock_df):
            result = fetcher.fetch()

        for item in result:
            assert isinstance(item["ticker"], str)
            assert len(item["ticker"]) == 4

    def test_fetch_skips_alpha_codes(self):
        """英字混在コード(130A等)はスキップされる。"""
        mock_df = pd.DataFrame({
            "コード": [7203, "130A", 6758],
            "銘柄名": ["トヨタ自動車", "テスト英字", "ソニーG"],
            "市場・商品区分": ["プライム（内国株式）"] * 3,
            "33業種区分": ["輸送用機器", "電気機器", "電気機器"],
        })
        fetcher = JpxStockListFetcher()

        with patch("pandas.read_excel", return_value=mock_df):
            result = fetcher.fetch()

        assert len(result) == 2
        tickers = [r["ticker"] for r in result]
        assert "7203" in tickers
        assert "6758" in tickers
