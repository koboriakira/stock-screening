from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

import requests

from stock_screener.shared.retry import retry_on_rate_limit

logger = logging.getLogger(__name__)

EDINET_API_BASE = "https://disclosure.edinet-fsa.go.jp/api/v2"


class EdinetClient:
    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    def get_documents(self, date: str) -> list[dict]:
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

    @staticmethod
    def ticker_to_sec_code(ticker_raw: str) -> str:
        code = ticker_raw.removesuffix(".T")
        if len(code) == 4:
            return code + "0"
        return code
