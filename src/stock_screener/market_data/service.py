from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import pandas as pd
import requests

from stock_screener.market_data.domain.financial_snapshot import FinancialSnapshot
from stock_screener.market_data.infrastructure.cache import FileCache
from stock_screener.market_data.infrastructure.yfinance_adapter import YFinanceSecurityRepository
from stock_screener.shared.json_output import NETWORK_ERROR, NO_DATA, RATE_LIMITED
from stock_screener.shared.types import Ticker


@dataclass(frozen=True)
class SnapshotFetchResult:
    """財務スナップショットの取得結果。snapshot と cache_hit をペアで保持する。"""

    snapshot: FinancialSnapshot
    cache_hit: bool


class FinancialSnapshotService:
    """CLI と YFinanceSecurityRepository の間に立ち、cache_hit を正確に判定する薄いサービス。

    リポジトリの公開 API は変更せず、リポジトリ呼び出しの前に FileCache を直接
    参照することでキャッシュの hit/miss を判定する。cache が None の場合(--no-cache)
    はキャッシュ確認自体をスキップし、常に cache_hit=False を返す。
    """

    def __init__(self, cache: FileCache | None = None) -> None:
        self._cache = cache
        self._repo = YFinanceSecurityRepository(cache=cache)

    def fetch(self, ticker: Ticker) -> SnapshotFetchResult:
        """財務スナップショットを取得する。"""
        cache_hit = False
        if self._cache is not None:
            cache_hit = self._cache.get(f"snapshot_{ticker.symbol}") is not None

        snapshot = self._repo.get_financial_snapshot(ticker)
        return SnapshotFetchResult(snapshot=snapshot, cache_hit=cache_hit)


@dataclass(frozen=True)
class DeclinerCandidate:
    """下落率ランキングの候補銘柄。"""

    ticker: str
    company_name: str
    change_pct: float
    price: float
    volume: int


def _classify_fetch_exception(e: Exception) -> tuple[str, str]:
    """フェッチ例外を (code, message) に分類する。cli._classify_fetch_exception と同型。"""
    if isinstance(e, requests.exceptions.HTTPError) and e.response is not None and e.response.status_code == 429:
        return RATE_LIMITED, "レート制限により取得に失敗しました"
    return NETWORK_ERROR, str(e) or "ネットワークエラーにより取得に失敗しました"


def rank_decliners(
    universe: list[dict],
    top_n: int,
    fetch: Callable[[str], pd.DataFrame],
    progress_cb: Callable[[int, int], None] | None = None,
) -> tuple[list[DeclinerCandidate], list[dict]]:
    """JPXユニバースを逐次走査し、前日比下落率上位 top_n 件を返す。

    universe は JpxStockListFetcher.fetch() と同型の dict リスト(ticker/company_name等)。
    fetch(ticker_symbol) で価格履歴(直近数日分)を取得し、最新2行から前日比 change_pct を計算する。
    第2戻り値は取得失敗銘柄のエラーリスト([{ticker, code, message}, ...])。
    progress_cb が指定されていれば (現在のインデックス, 総数) を都度呼ぶ。

    全銘柄を逐次取得するため実行時間は数十分オーダーになりうる(screen コマンドと同様の
    非機能特性。独自キャッシュや一括バッチ取得は導入しない)。
    """
    candidates: list[DeclinerCandidate] = []
    errors: list[dict] = []
    total = len(universe)

    for i, row in enumerate(universe, 1):
        ticker_symbol = f"{row['ticker']}.T"
        try:
            hist = fetch(ticker_symbol)
        except Exception as e:
            code, message = _classify_fetch_exception(e)
            errors.append({"ticker": ticker_symbol, "code": code, "message": message})
        else:
            if hist.empty or len(hist) < 2:
                errors.append(
                    {"ticker": ticker_symbol, "code": NO_DATA, "message": "価格データが取得できませんでした"},
                )
            else:
                last = hist.iloc[-1]
                prev = hist.iloc[-2]
                price = float(last["Close"])
                prev_close = float(prev["Close"])
                change_pct = round((price / prev_close - 1) * 100, 2)
                candidates.append(
                    DeclinerCandidate(
                        ticker=ticker_symbol,
                        company_name=row["company_name"],
                        change_pct=change_pct,
                        price=price,
                        volume=int(last["Volume"]),
                    ),
                )

        if progress_cb is not None:
            progress_cb(i, total)

    candidates.sort(key=lambda c: c.change_pct)
    return candidates[:top_n], errors
