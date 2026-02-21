from __future__ import annotations

import argparse
import csv
import logging
from pathlib import Path

from stock_screener.discovery.domain.candidate import ScreeningResult
from stock_screener.discovery.domain.universe import Universe
from stock_screener.discovery.service import ScreeningService
from stock_screener.market_data.infrastructure.jpx_stock_list import JpxStockListFetcher
from stock_screener.market_data.infrastructure.yfinance_adapter import YFinanceSecurityRepository

logger = logging.getLogger(__name__)

TEST_MODE_LIMIT = 5


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="stock-screener",
        description="小型バリュー株スクリーニングシステム",
    )
    parser.add_argument("--verbose", action="store_true", help="詳細ログを出力")

    subparsers = parser.add_subparsers(dest="command", required=True)

    screen_parser = subparsers.add_parser("screen", help="スクリーニングを実行")
    screen_parser.add_argument("--top", type=int, default=30, help="上位N銘柄を出力 (default: 30)")
    screen_parser.add_argument("--output", type=str, default=None, help="CSV出力パス")
    screen_parser.add_argument("--test", action="store_true", help="テストモード (5銘柄のみ)")

    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format="%(levelname)s: %(message)s")

    if args.command == "screen":
        _run_screen(args)


def _run_screen(args: argparse.Namespace) -> None:
    logger.info("JPX銘柄リストを取得中...")
    fetcher = JpxStockListFetcher()
    jpx_data = fetcher.fetch()
    universe = Universe.from_jpx_data(jpx_data)

    if args.test:
        universe = universe.limit(TEST_MODE_LIMIT)
        logger.info("テストモード: %d銘柄に制限", TEST_MODE_LIMIT)

    logger.info("ユニバース: %d銘柄", len(universe))

    repo = YFinanceSecurityRepository()
    logger.info("財務データを取得中...")
    for sec in universe.securities:
        snap = repo.get_financial_snapshot(sec.ticker)
        sec.financial_snapshot = snap

    service = ScreeningService()
    result = service.execute(universe.securities, top_n=args.top)

    _print_result(result)

    if args.output:
        _write_csv(result, Path(args.output))
        logger.info("CSV出力: %s", args.output)


def _print_result(result: ScreeningResult) -> None:
    print(f"\n{'='*80}")
    print(f"スクリーニング結果 ({result.timestamp.strftime('%Y-%m-%d %H:%M')} UTC)")
    print(f"ユニバース: {result.total_universe} → ハードフィルタ後: {result.after_hard_filter}"
          f" → ソフトフィルタ後: {result.after_soft_filter}")
    print(f"{'='*80}")
    print(f"{'順位':>4} {'ティッカー':<10} {'銘柄名':<20} {'総合':>6} {'割安':>6} {'質':>6} {'変化':>6}")
    print(f"{'-'*80}")
    for c in result.candidates:
        print(
            f"{c.rank:>4} {c.security.ticker.symbol:<10} {c.security.company_name:<20}"
            f" {c.score.total:>6.1f} {c.score.value:>6.1f} {c.score.quality:>6.1f} {c.score.momentum:>6.1f}",
        )
    print()


def _write_csv(result: ScreeningResult, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "rank", "ticker", "company_name", "sector",
                "total_score", "value_score", "quality_score", "momentum_score",
                "per", "pbr", "roe", "market_cap",
            ],
        )
        writer.writeheader()
        for c in result.candidates:
            snap = c.security.financial_snapshot
            writer.writerow({
                "rank": c.rank,
                "ticker": c.security.ticker.symbol,
                "company_name": c.security.company_name,
                "sector": c.security.sector,
                "total_score": round(c.score.total, 2),
                "value_score": round(c.score.value, 2),
                "quality_score": round(c.score.quality, 2),
                "momentum_score": round(c.score.momentum, 2),
                "per": snap.per,
                "pbr": snap.pbr,
                "roe": snap.roe,
                "market_cap": snap.market_cap,
            })
