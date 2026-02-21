from __future__ import annotations

import pandas as pd

JPX_URL = "https://www.jpx.co.jp/markets/statistics-equities/misc/tvdivq0000001vg2-att/data_j.xls"


class JpxStockListFetcher:
    def fetch(self, url: str = JPX_URL) -> list[dict]:
        df = pd.read_excel(url)
        results = []
        for _, row in df.iterrows():
            code_raw = str(row["コード"]).strip()
            # 数字のみの4桁コードに正規化(130A等の英字混在コードはスキップ)
            if code_raw.replace(".", "").isdigit():
                ticker = str(int(float(code_raw)))
            else:
                continue
            market_raw = str(row["市場・商品区分"])
            market = market_raw.split("（", maxsplit=1)[0] if "（" in market_raw else market_raw
            results.append({
                "ticker": ticker,
                "company_name": str(row["銘柄名"]),
                "sector": str(row["33業種区分"]),
                "market": market,
            })
        return results
