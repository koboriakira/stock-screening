from __future__ import annotations

from dataclasses import dataclass

from stock_screener.market_data.domain.financial_snapshot import FinancialSnapshot
from stock_screener.market_data.infrastructure.cache import FileCache
from stock_screener.market_data.infrastructure.yfinance_adapter import YFinanceSecurityRepository
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
