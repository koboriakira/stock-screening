from __future__ import annotations

import logging

import requests

from stock_screener.evaluation.domain.check import CheckStatus
from stock_screener.evaluation.infrastructure.edinet_client import EdinetClient
from stock_screener.evaluation.infrastructure.yfinance_eval_provider import (
    YFinanceEvaluationDataProvider,
)
from stock_screener.shared.types import Ticker

logger = logging.getLogger(__name__)


class EdinetEvaluationDataProvider(YFinanceEvaluationDataProvider):
    def __init__(self, edinet_client: EdinetClient | None = None) -> None:
        self._edinet_client = edinet_client

    def check_accounting_fraud(self, ticker: Ticker) -> CheckStatus:
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
