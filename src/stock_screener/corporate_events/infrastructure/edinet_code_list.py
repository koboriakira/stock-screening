from __future__ import annotations

import csv
import io
import logging
import zipfile

import requests

from stock_screener.market_data.infrastructure.cache import FileCache

logger = logging.getLogger(__name__)

EDINET_CODE_LIST_URL = "https://disclosure2dl.edinet-fsa.go.jp/searchdocument/codelist/Edinetcode.zip"

_CSV_MEMBER_NAME = "EdinetcodeDlInfo.csv"
_CACHE_KEY = "edinet_code_list"
_COL_EDINET_CODE = 0
_COL_SEC_CODE = 11

# 実データ(2026-07-18時点、11,348件)で確認した構造:
# 1行目=タイトル行(ダウンロード実行日・件数)、2行目=ヘッダ行、3行目以降がデータ。
# エンコーディングは Shift-JIS(cp932)。証券コード列は5桁ゼロ埋め済みで、
# 非上場の発行会社は空文字列になる。
_DATA_START_ROW = 2


class EdinetCodeListFetcher:
    """EDINETコードリスト(発行会社EDINETコード⇔証券コード対応表)を取得するフェッチャ。

    更新頻度が低いため、呼び出し側は長め(例: 168h/1週間)のTTLでキャッシュを
    渡すことを想定する。
    """

    def __init__(self, cache: FileCache | None = None) -> None:
        self._cache = cache

    def fetch(self) -> list[dict]:
        """ZIPをダウンロードしCSVを解凍・パースする。

        [{"edinet_code": ..., "sec_code": ...}, ...] を返す。sec_code は非上場の
        発行会社の場合、空文字列になる。
        """
        if self._cache is not None:
            cached = self._cache.get(_CACHE_KEY)
            if cached is not None:
                return cached

        resp = requests.get(EDINET_CODE_LIST_URL, timeout=30)
        resp.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            raw = zf.read(_CSV_MEMBER_NAME)
        text = raw.decode("cp932")
        rows = list(csv.reader(io.StringIO(text)))

        results = [
            {"edinet_code": row[_COL_EDINET_CODE], "sec_code": row[_COL_SEC_CODE]}
            for row in rows[_DATA_START_ROW:]
            if len(row) > _COL_SEC_CODE
        ]

        if self._cache is not None:
            self._cache.set(_CACHE_KEY, results)
        return results

    def find_issuer_edinet_code(self, sec_code: str) -> str | None:
        """5桁証券コードから発行会社のEDINETコードを引く。見つからない場合は None。"""
        for row in self.fetch():
            if row["sec_code"] == sec_code:
                return row["edinet_code"]
        return None
