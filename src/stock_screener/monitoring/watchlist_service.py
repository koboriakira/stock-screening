from __future__ import annotations

import logging

import yfinance as yf

from stock_screener.monitoring.domain.bottom_detector import BottomSignal, detect_bottom_signals
from stock_screener.monitoring.domain.watchlist import WatchlistEntry
from stock_screener.monitoring.infrastructure.slack_notifier import send_notification
from stock_screener.monitoring.infrastructure.watchlist_repository import WatchlistRepository

logger = logging.getLogger(__name__)

HISTORY_PERIOD = "6mo"

_LEVEL_LABELS = {
    "buy_candidate": "買い検討",
    "attention": "注目",
}


class WatchlistMonitoringService:
    """ウォッチリスト銘柄の底打ちシグナルモニタリング。"""

    def __init__(
        self,
        watchlist_repo: WatchlistRepository | None = None,
    ) -> None:
        self._watchlist_repo = watchlist_repo or WatchlistRepository()

    def execute(self) -> list[dict]:
        """ウォッチリスト全銘柄のシグナル検出を実行する。

        Returns:
            list of {ticker, name, signal: BottomSignal, notified: bool}
        """
        watchlist = self._watchlist_repo.load()
        results = []

        for entry in watchlist.entries:
            logger.info("Watchlist check: %s (%s)", entry.ticker, entry.name)

            hist = self._fetch_history(entry.ticker)
            if hist is None or hist.empty:
                logger.warning("%s: data fetch failed, skipping", entry.ticker)
                continue

            signal = detect_bottom_signals(entry.ticker, hist)
            notified = False

            if signal.level:
                label = _LEVEL_LABELS.get(signal.level, signal.level)
                msg = self._format_message(entry, signal, label)
                notified = send_notification(msg)

            results.append({
                "ticker": entry.ticker,
                "name": entry.name,
                "signal": signal,
                "notified": notified,
            })

        return results

    def _fetch_history(self, ticker: str) -> object | None:
        try:
            stock = yf.Ticker(ticker)
            return stock.history(period=HISTORY_PERIOD)
        except Exception:
            logger.exception("%s: history fetch error", ticker)
            return None

    def _format_message(self, entry: WatchlistEntry, signal: BottomSignal, label: str) -> str:
        details = signal.details
        return (
            f"[WL:{label}] {entry.ticker} ({entry.name})\n"
            f"スコア: {signal.score}/{signal.max_score}\n"
            f"RSI: {details.get('rsi', '-')} | "
            f"BB位置: {details.get('bb_position', '-')} | "
            f"MACD: {details.get('macd_histogram', '-')} | "
            f"出来高比: {details.get('volume_ratio', '-')}\n"
            f"RSI:{_bool_mark(signal.rsi_signal)} "
            f"BB:{_bool_mark(signal.bb_signal)} "
            f"MACD:{_bool_mark(signal.macd_signal)} "
            f"出来高:{_bool_mark(signal.volume_confirmed)} "
            f"MA:{_bool_mark(signal.ma_crossover)}"
        )


def _bool_mark(value: bool) -> str:
    return "o" if value else "x"
