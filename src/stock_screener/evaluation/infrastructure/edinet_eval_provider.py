from __future__ import annotations

import logging

import requests

from stock_screener.edinet.client import EdinetClient
from stock_screener.evaluation.domain.check import CheckStatus
from stock_screener.evaluation.infrastructure.yfinance_eval_provider import (
    YFinanceEvaluationDataProvider,
)
from stock_screener.shared.types import Ticker

logger = logging.getLogger(__name__)


class EdinetEvaluationDataProvider(YFinanceEvaluationDataProvider):
    """EDINET API を利用した評価データプロバイダ。

    YFinanceEvaluationDataProvider を継承し、Gate1 の不正会計チェック(1-1)と
    継続企業の前提注記チェック(1-2)を EDINET API のデータで実装する。
    API キー未設定時(edinet_client=None)はスタブにフォールバックする。
    """

    def __init__(self, edinet_client: EdinetClient | None = None) -> None:
        self._edinet_client = edinet_client

    def check_accounting_fraud(self, ticker: Ticker) -> CheckStatus:
        """過去3年間の訂正有価証券報告書(docTypeCode=130)の有無を確認する。

        訂正報告書が存在する場合は NEEDS_REVIEW、存在しない場合は PASS を返す。
        API 未設定時またはリクエスト失敗時は NEEDS_REVIEW を返す。
        """
        if self._edinet_client is None:
            return CheckStatus.NEEDS_REVIEW
        try:
            sec_code = self._edinet_client.ticker_to_sec_code(ticker.symbol)
            filings = self._edinet_client.find_filings_by_sec_code(
                sec_code, doc_type_codes=["130"], days=1095,
            )
            if filings:
                return CheckStatus.NEEDS_REVIEW
            return CheckStatus.PASS
        except requests.exceptions.RequestException:
            logger.warning("EDINET check_accounting_fraud failed for %s", ticker.symbol)
            return CheckStatus.NEEDS_REVIEW

    def check_going_concern(self, ticker: Ticker) -> CheckStatus:
        """最新の有価証券報告書(docTypeCode=120)の存在を確認する。

        現在は書類の存在確認のみ行い、XBRL 内容の解析は行わないため、
        常に NEEDS_REVIEW を返す。API 未設定時も同様。
        """
        if self._edinet_client is None:
            return CheckStatus.NEEDS_REVIEW
        try:
            sec_code = self._edinet_client.ticker_to_sec_code(ticker.symbol)
            filings = self._edinet_client.find_filings_by_sec_code(
                sec_code, doc_type_codes=["120"], days=365,
            )
            if filings:
                latest = filings[0]
                logger.info(
                    "Latest annual report for %s: %s (%s)",
                    ticker.symbol,
                    latest.get("docDescription"),
                    latest.get("submitDateTime"),
                )
            return CheckStatus.NEEDS_REVIEW
        except requests.exceptions.RequestException:
            logger.warning("EDINET check_going_concern failed for %s", ticker.symbol)
            return CheckStatus.NEEDS_REVIEW
