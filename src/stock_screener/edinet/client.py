from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

import requests

from stock_screener.shared.retry import retry_on_rate_limit

logger = logging.getLogger(__name__)

EDINET_API_BASE = "https://disclosure.edinet-fsa.go.jp/api/v2"


class EdinetClient:
    """EDINET API v2 クライアント。書類一覧の取得と証券コード検索を提供する。"""

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    def get_documents(self, date: str) -> list[dict]:
        """指定日の提出書類一覧を取得する。"""
        url = f"{EDINET_API_BASE}/documents.json"
        params = {
            "date": date,
            "type": 2,
            "Subscription-Key": self._api_key,
        }
        def _request() -> list[dict]:
            resp = requests.get(url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            return data.get("results", [])

        try:
            return retry_on_rate_limit(_request, max_retries=2, base_delay=2.0, default=[])
        except (ValueError, KeyError):
            logger.warning("EDINET API invalid response for date=%s", date)
            return []

    def find_filings_by_sec_code(
        self,
        sec_code: str,
        doc_type_codes: list[str],
        days: int,
    ) -> list[dict]:
        """証券コードと書類種別で過去N日間の提出書類を検索する。

        Args:
            sec_code: 5桁の証券コード(例: '72030')。
            doc_type_codes: 対象とする書類種別コードのリスト(例: ['120', '130'])。
            days: 過去何日分を検索するか。

        Returns:
            条件に合致する書類メタデータのリスト。
        """
        matches: list[dict] = []
        today = datetime.now(tz=UTC).date()
        for i in range(days):
            date = (today - timedelta(days=i)).isoformat()
            documents = self.get_documents(date)
            for doc in documents:
                doc_sec = doc.get("secCode")
                doc_type = doc.get("docTypeCode")
                if doc_sec == sec_code and doc_type in doc_type_codes:
                    matches.append(doc)
        return matches

    def find_filings_by_issuer_edinet_code(
        self,
        issuer_edinet_code: str,
        doc_type_codes: list[str],
        days: int,
    ) -> list[dict]:
        """発行会社のEDINETコードと書類種別で過去N日間の提出書類を検索する。

        secCodeは提出者(保有者)側のコードのため、大量保有報告の対象銘柄検索には
        issuerEdinetCodeで絞り込む必要がある。

        Args:
            issuer_edinet_code: 発行会社のEDINETコード(例: 'E00004')。
            doc_type_codes: 対象とする書類種別コードのリスト(例: ['350', '360'])。
            days: 過去何日分を検索するか。

        Returns:
            条件に合致する書類メタデータのリスト。
        """
        matches: list[dict] = []
        today = datetime.now(tz=UTC).date()
        for i in range(days):
            date = (today - timedelta(days=i)).isoformat()
            documents = self.get_documents(date)
            for doc in documents:
                doc_issuer_code = doc.get("issuerEdinetCode")
                doc_type = doc.get("docTypeCode")
                if doc_issuer_code == issuer_edinet_code and doc_type in doc_type_codes:
                    matches.append(doc)
        return matches

    @staticmethod
    def ticker_to_sec_code(ticker_raw: str) -> str:
        """ティッカーシンボルを EDINET 用の5桁証券コードに変換する。

        末尾の '.T' を除去し、4桁の場合は末尾に '0' を付与して5桁にする。
        """
        code = ticker_raw.removesuffix(".T")
        if len(code) == 4:
            return code + "0"
        return code
