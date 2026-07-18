from __future__ import annotations

import logging

import requests

from stock_screener.corporate_events.domain.earnings_date import EarningsDate
from stock_screener.corporate_events.infrastructure.jquants_client import JQuantsClient
from stock_screener.shared.types import Ticker

logger = logging.getLogger(__name__)


class JQuantsEarningsDateProvider:
    """J-Quants個人向けAPIから決算発表予定日を取得するプロバイダ。

    client が None(APIキー未設定)の場合は NEEDS_REVIEW 相当として None を返す。
    該当データがない場合も None を返す(両者はこの層では区別しない。呼び出し側の
    CLI で needs_review/ok の判定を行う)。
    """

    def __init__(self, client: JQuantsClient | None) -> None:
        self._client = client

    def get_earnings_date(self, ticker: Ticker) -> EarningsDate | None:
        """指定銘柄の決算発表予定日を取得する。

        client 未設定時、またはネットワークエラー・該当データなしの場合は None。
        """
        if self._client is None:
            return None

        try:
            results = self._client.get_earnings_calendar(code=ticker.code)
        except requests.exceptions.RequestException:
            logger.warning("J-Quants earnings calendar fetch failed for %s", ticker.symbol)
            return None

        if not results:
            return None

        return EarningsDate.from_jquants_entry(ticker.symbol, results[0])
