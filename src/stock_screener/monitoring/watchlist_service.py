from __future__ import annotations

import json
import logging
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import yfinance as yf

from stock_screener.monitoring.domain.bottom_detector import BottomSignal, detect_bottom_signals
from stock_screener.monitoring.domain.watchlist import (
    ScoreRecord,
    WatchlistEntry,
    WatchlistParams,
)
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

    def add_entry(
        self,
        ticker: str,
        name: str,
        memo: str = "",
        params: WatchlistParams | None = None,
    ) -> WatchlistEntry:
        """ウォッチリストに銘柄を追加し、現在値を自動取得して registered_price に記録する。"""
        registered_price = self._fetch_current_price(ticker)
        today = datetime.now(tz=UTC).date()

        entry = WatchlistEntry(
            ticker=ticker,
            name=name,
            added_date=today,
            memo=memo,
            registered_price=registered_price,
            params=params or WatchlistParams(),
        )
        watchlist = self._watchlist_repo.load()
        watchlist.add(entry)
        self._watchlist_repo.save(watchlist)
        return entry

    def execute(
        self,
        dry_run: bool = False,
        output_path: Path | None = None,
    ) -> list[dict]:
        """ウォッチリスト全銘柄のシグナル検出を実行する。

        Args:
            dry_run: True の場合、通知送信とスコア履歴の保存をスキップ
            output_path: 指定時に JSON レポートを出力

        Returns:
            list of result dicts
        """
        watchlist = self._watchlist_repo.load()
        results = []
        today = datetime.now(tz=UTC).date()
        updated_watchlist = watchlist

        for entry in watchlist.entries:
            logger.info("Watchlist check: %s (%s)", entry.ticker, entry.name)

            hist = self._fetch_history(entry.ticker)
            if hist is None or hist.empty:
                logger.warning("%s: data fetch failed, skipping", entry.ticker)
                continue

            current_price = self._fetch_current_price(entry.ticker)

            # 前日スコアの取得
            previous_score = entry.score_history[-1].score if entry.score_history else None

            signal = detect_bottom_signals(
                entry.ticker,
                hist,
                volume_threshold=entry.params.volume_threshold,
                previous_score=previous_score,
            )

            # クールダウン判定
            cooldown_remaining = self._calc_cooldown_remaining(entry, today)
            in_cooldown = cooldown_remaining > 0

            notified = False
            if signal.level and not in_cooldown and not dry_run:
                label = _LEVEL_LABELS.get(signal.level, signal.level)
                msg = self._format_message(entry, signal, label, current_price)
                notified = send_notification(msg)
                if notified:
                    updated_watchlist = updated_watchlist.update_entry(
                        entry.ticker,
                        last_notified_at=today,
                    )

            # シグナル状態を dict に変換
            current_signals = {
                "rsi": signal.rsi_signal,
                "bb": signal.bb_signal,
                "macd": signal.macd_signal,
                "volume": signal.volume_confirmed,
                "ma": signal.ma_crossover,
            }

            # スコア変動理由の算出
            score_change_reasons = _calc_score_change_reasons(entry, current_signals)

            # スコア履歴の追記
            if not dry_run:
                new_record = ScoreRecord(date=today, score=signal.score, signals=current_signals)
                new_history = [*entry.score_history, new_record]
                updated_watchlist = updated_watchlist.update_entry(
                    entry.ticker,
                    score_history=new_history,
                )

            # 騰落率の計算
            price_change_pct = None
            if entry.registered_price is not None and current_price is not None:
                price_change_pct = (current_price - entry.registered_price) / entry.registered_price

            results.append({
                "ticker": entry.ticker,
                "name": entry.name,
                "signal": signal,
                "notified": notified,
                "current_price": current_price,
                "registered_price": entry.registered_price,
                "price_change_pct": price_change_pct,
                "cooldown_remaining_days": cooldown_remaining,
                "score_change_reasons": score_change_reasons,
            })

        # 保存
        if not dry_run:
            self._watchlist_repo.save(updated_watchlist)

        # JSON レポート出力
        if output_path is not None:
            self._write_json_report(results, output_path)

        return results

    def _fetch_history(self, ticker: str) -> object | None:
        try:
            stock = yf.Ticker(ticker)
            return stock.history(period=HISTORY_PERIOD)
        except Exception:
            logger.exception("%s: history fetch error", ticker)
            return None

    def _fetch_current_price(self, ticker: str) -> float | None:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            return info.get("currentPrice")
        except Exception:
            logger.exception("%s: current price fetch error", ticker)
            return None

    def _calc_cooldown_remaining(self, entry: WatchlistEntry, today: date) -> int:
        if entry.last_notified_at is None:
            return 0
        cooldown_end = entry.last_notified_at + timedelta(days=entry.params.cooldown_days)
        remaining = (cooldown_end - today).days
        return max(0, remaining)

    def _format_message(
        self,
        entry: WatchlistEntry,
        signal: BottomSignal,
        label: str,
        current_price: float | None,
    ) -> str:
        details = signal.details
        lines = [
            f"[WL:{label}] {entry.ticker} ({entry.name})",
            f"スコア: {signal.score}/{signal.max_score}",
        ]

        # スコアデルタ
        if signal.score_delta is not None:
            delta_str = f"+{signal.score_delta}" if signal.score_delta >= 0 else str(signal.score_delta)
            lines[-1] += f" (前日比: {delta_str})"

        # 現在値と登録時比
        if current_price is not None:
            price_line = f"現在値: {current_price:,.0f}"
            if entry.registered_price is not None:
                pct = (current_price - entry.registered_price) / entry.registered_price * 100
                price_line += f" (登録時比: {pct:+.1f}%)"
            lines.append(price_line)

        lines.append(
            f"RSI: {details.get('rsi', '-')} | "
            f"BB位置: {details.get('bb_position', '-')} | "
            f"MACD: {details.get('macd_histogram', '-')} | "
            f"出来高比: {details.get('volume_ratio', '-')}",
        )
        lines.append(
            f"RSI:{_bool_mark(signal.rsi_signal)} "
            f"BB:{_bool_mark(signal.bb_signal)} "
            f"MACD:{_bool_mark(signal.macd_signal)} "
            f"出来高:{_bool_mark(signal.volume_confirmed)} "
            f"MA:{_bool_mark(signal.ma_crossover)}",
        )
        return "\n".join(lines)

    def _write_json_report(self, results: list[dict], path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        report = []
        for r in results:
            sig = r["signal"]
            entry_data = {
                "ticker": r["ticker"],
                "name": r["name"],
                "score": sig.score,
                "max_score": sig.max_score,
                "level": sig.level,
                "score_delta": sig.score_delta,
                "current_price": r["current_price"],
                "registered_price": r["registered_price"],
                "price_change_pct": r["price_change_pct"],
                "cooldown_remaining_days": r["cooldown_remaining_days"],
                "notified": r["notified"],
                "details": sig.details,
                "signals": {
                    "rsi": sig.rsi_signal,
                    "bb": sig.bb_signal,
                    "macd": sig.macd_signal,
                    "volume": sig.volume_confirmed,
                    "ma_crossover": sig.ma_crossover,
                },
            }
            report.append(entry_data)

        with path.open("w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)


_SIGNAL_LABELS = {
    "rsi": "RSI",
    "bb": "BB",
    "macd": "MACD",
    "volume": "出来高",
    "ma": "MA",
}


def _calc_score_change_reasons(
    entry: WatchlistEntry,
    current_signals: dict[str, bool],
) -> list[str]:
    """前日のシグナル状態と比較してスコア変動理由を算出する。"""
    if not entry.score_history:
        return []
    prev_signals = entry.score_history[-1].signals
    if prev_signals is None:
        return []
    reasons = []
    for key, current in current_signals.items():
        prev = prev_signals.get(key, False)
        label = _SIGNAL_LABELS.get(key, key)
        if current and not prev:
            reasons.append(f"{label}点灯")
        elif not current and prev:
            reasons.append(f"{label}消灯")
    return reasons


def _bool_mark(value: bool) -> str:
    return "o" if value else "x"
