from __future__ import annotations

import io
import zipfile
from unittest.mock import MagicMock, patch

from stock_screener.corporate_events.infrastructure.edinet_code_list import (
    EDINET_CODE_LIST_URL,
    EdinetCodeListFetcher,
)
from stock_screener.market_data.infrastructure.cache import FileCache

# 実データ(2026-07-18 ダウンロード)で確認した構造を再現したフィクスチャ:
# 1行目=タイトル行(ダウンロード実行日・件数)、2行目=ヘッダ行、3行目以降=データ。
# エンコーディングは Shift-JIS(cp932)。証券コード列(index 11)は5桁ゼロ埋め済みで、
# 非上場の発行会社は空文字列になる。
_FIXTURE_CSV = (
    "ダウンロード実行日,2026年07月18日現在,件数,3件\r\n"
    "ＥＤＩＮＥＴコード,提出者種別,上場区分,連結の有無,資本金,決算日,提出者名,"
    "提出者名（英字）,提出者名（ヨミ）,所在地,提出者業種,証券コード,提出者法人番号\r\n"
    '"E00004","内国法人・組合","上場","有","1491","5月31日","カネコ種苗株式会社",'
    '"KANEKO SEEDS CO., LTD.","カネコシュビョウカブシキガイシャ","前橋市古市町一丁目５０番地１２",'
    '"水産・農林業","13760","5070001000715"\r\n'
    '"E00011","内国法人・組合","上場","有","50074","12月31日","住友林業株式会社",'
    '"Sumitomo Forestry Co.,Ltd.","スミトモリンギョウカブシキガイシャ","千代田区大手町一丁目３番２号",'
    '"建設業","19110","4010001090011"\r\n'
    '"E00017","内国法人・組合","非上場","有","2485","3月31日","株式会社ホウスイ",'
    '"HOHSUI  CORPORATION","カブシキガイシャホウスイ","江東区豊洲六丁目６番３号",'
    '"卸売業","","9010001034921"\r\n'
)


def _make_zip_bytes() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("EdinetcodeDlInfo.csv", _FIXTURE_CSV.encode("cp932"))
    return buf.getvalue()


def _mock_response() -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.content = _make_zip_bytes()
    return resp


class TestEdinetCodeListFetcherFetch:
    def test_skips_title_and_header_rows(self):
        with patch("requests.get", return_value=_mock_response()) as mock_get:
            fetcher = EdinetCodeListFetcher()
            rows = fetcher.fetch()

        assert len(rows) == 3
        mock_get.assert_called_once()
        assert mock_get.call_args[0][0] == EDINET_CODE_LIST_URL

    def test_maps_edinet_code_and_sec_code_columns(self):
        with patch("requests.get", return_value=_mock_response()):
            fetcher = EdinetCodeListFetcher()
            rows = fetcher.fetch()

        assert rows[0] == {"edinet_code": "E00004", "sec_code": "13760"}
        assert rows[1] == {"edinet_code": "E00011", "sec_code": "19110"}

    def test_handles_empty_sec_code_for_unlisted_issuer(self):
        with patch("requests.get", return_value=_mock_response()):
            fetcher = EdinetCodeListFetcher()
            rows = fetcher.fetch()

        assert rows[2] == {"edinet_code": "E00017", "sec_code": ""}


class TestEdinetCodeListFetcherCache:
    def test_uses_cache_when_present(self, tmp_path):
        cache = FileCache(cache_dir=tmp_path, ttl_hours=168)
        cache.set("edinet_code_list", [{"edinet_code": "E99999", "sec_code": "00000"}])
        fetcher = EdinetCodeListFetcher(cache=cache)

        with patch("requests.get") as mock_get:
            rows = fetcher.fetch()

        mock_get.assert_not_called()
        assert rows == [{"edinet_code": "E99999", "sec_code": "00000"}]

    def test_populates_cache_after_fetch(self, tmp_path):
        cache = FileCache(cache_dir=tmp_path, ttl_hours=168)
        fetcher = EdinetCodeListFetcher(cache=cache)

        with patch("requests.get", return_value=_mock_response()):
            fetcher.fetch()

        cached = cache.get("edinet_code_list")
        assert cached is not None
        assert len(cached) == 3


class TestEdinetCodeListFetcherFindIssuerEdinetCode:
    def test_returns_matching_edinet_code(self):
        with patch("requests.get", return_value=_mock_response()):
            fetcher = EdinetCodeListFetcher()
            result = fetcher.find_issuer_edinet_code("13760")

        assert result == "E00004"

    def test_returns_none_when_not_found(self):
        with patch("requests.get", return_value=_mock_response()):
            fetcher = EdinetCodeListFetcher()
            result = fetcher.find_issuer_edinet_code("99999")

        assert result is None
