from __future__ import annotations

import logging

import requests

from stock_screener.corporate_events.domain.large_holding import LargeHoldingFiling
from stock_screener.corporate_events.infrastructure.edinet_code_list import EdinetCodeListFetcher
from stock_screener.edinet.client import EdinetClient
from stock_screener.market_data.infrastructure.cache import FileCache
from stock_screener.shared.types import Ticker

logger = logging.getLogger(__name__)

_LARGE_HOLDING_DOC_TYPE_CODES = ["350", "360"]
_CODE_LIST_CACHE_TTL_HOURS = 168


class EdinetLargeHoldingProvider:
    """EDINET大量保有報告書(5%ルール、docTypeCode 350/360)を取得するプロバイダ。

    edinet_client が None(API キー未設定)の場合は NEEDS_REVIEW 相当として
    None を返す。訂正・変更報告(parentDocID連鎖)の解決は行わず、生データを
    そのまま返す。
    """

    def __init__(
        self,
        edinet_client: EdinetClient | None,
        code_list_fetcher: EdinetCodeListFetcher | None = None,
    ) -> None:
        self._edinet_client = edinet_client
        self._code_list_fetcher = code_list_fetcher or EdinetCodeListFetcher(
            cache=FileCache(ttl_hours=_CODE_LIST_CACHE_TTL_HOURS),
        )

    def get_large_holdings(self, ticker: Ticker, days: int = 90) -> list[LargeHoldingFiling] | None:
        """指定銘柄の大量保有報告書を過去N日分取得する。

        edinet_client 未設定時は None。発行会社の EDINET コードが見つからない
        場合、またはネットワークエラー時はそれぞれ空リスト/None を返す。
        """
        if self._edinet_client is None:
            return None

        sec_code = EdinetClient.ticker_to_sec_code(ticker.symbol)
        try:
            issuer_edinet_code = self._code_list_fetcher.find_issuer_edinet_code(sec_code)
        except requests.exceptions.RequestException:
            logger.warning("EDINET code list fetch failed for %s", ticker.symbol)
            return None

        if issuer_edinet_code is None:
            return []

        try:
            docs = self._edinet_client.find_filings_by_issuer_edinet_code(
                issuer_edinet_code,
                doc_type_codes=_LARGE_HOLDING_DOC_TYPE_CODES,
                days=days,
            )
        except requests.exceptions.RequestException:
            logger.warning("EDINET large holdings fetch failed for %s", ticker.symbol)
            return None

        return [LargeHoldingFiling.from_edinet_doc(doc) for doc in docs]
