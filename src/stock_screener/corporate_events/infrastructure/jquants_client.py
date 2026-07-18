from __future__ import annotations

import logging

import requests

from stock_screener.shared.retry import retry_on_rate_limit

logger = logging.getLogger(__name__)

J_QUANTS_API_BASE = "https://api.jquants.com/v2"


class JQuantsClient:
    """J-Quants個人向けAPI クライアント。

    認証方式は未検証(単一APIキーをヘッダに渡す最も単純な実装)。
    実キー取得後、リフレッシュトークン方式等への修正が必要になる可能性がある。
    """

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    def get_earnings_calendar(self, code: str | None = None) -> list[dict]:
        """決算発表予定日一覧を取得する。/equities/earnings-calendar エンドポイント。

        レスポンスフィールド: Date(発表予定日), Code, CoName, FY, FQ, SectorNm,
        Section, pagination_key。
        code指定時はその銘柄のみに絞り込む(APIがフィルタ非対応ならクライアント側でフィルタする)。
        """
        url = f"{J_QUANTS_API_BASE}/equities/earnings-calendar"
        headers = {"Authorization": f"Bearer {self._api_key}"}
        params: dict[str, str] = {}
        if code is not None:
            params["code"] = code

        def _request() -> list[dict]:
            resp = requests.get(url, headers=headers, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            return data.get("earnings_calendar", [])

        try:
            results = retry_on_rate_limit(_request, max_retries=2, base_delay=2.0, default=[])
        except (ValueError, KeyError):
            logger.warning("J-Quants API invalid response for earnings-calendar")
            return []

        if code is not None:
            results = [r for r in results if r.get("Code") == code]
        return results
