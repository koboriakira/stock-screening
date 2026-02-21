from __future__ import annotations

import argparse
import csv
import logging
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

from stock_screener.discovery.domain.candidate import ScreeningResult
from stock_screener.discovery.domain.universe import Universe
from stock_screener.discovery.service import ScreeningService
from stock_screener.evaluation.domain.evaluation_report import EvaluationReport
from stock_screener.evaluation.domain.evaluation_target import EvaluationTarget
from stock_screener.evaluation.infrastructure.edinet_client import EdinetClient
from stock_screener.evaluation.infrastructure.edinet_eval_provider import EdinetEvaluationDataProvider
from stock_screener.evaluation.infrastructure.yfinance_eval_provider import YFinanceEvaluationDataProvider
from stock_screener.evaluation.service import EvaluationService
from stock_screener.market_data.infrastructure.cache import FileCache
from stock_screener.market_data.infrastructure.jpx_stock_list import JpxStockListFetcher
from stock_screener.market_data.infrastructure.yfinance_adapter import YFinanceSecurityRepository

logger = logging.getLogger(__name__)

TEST_MODE_LIMIT = 5
DEFAULT_DATA_DIR = Path.home() / ".local" / "share" / "stock-screener" / "results"


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
    screen_parser.add_argument("--no-cache", action="store_true", help="キャッシュを使用しない")

    evaluate_parser = subparsers.add_parser("evaluate", help="スクリーニング結果を評価")
    evaluate_parser.add_argument("--input", type=str, required=True, help="スクリーニング結果CSV")
    evaluate_parser.add_argument("--output", type=str, default=None, help="評価結果CSV出力パス")

    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format="%(levelname)s: %(message)s")

    try:
        if args.command == "screen":
            _run_screen(args)
        elif args.command == "evaluate":
            _run_evaluate(args)
    except FileNotFoundError as e:
        logger.error("ファイルが見つかりません: %s", e)
        raise SystemExit(1) from e
    except Exception as e:
        logger.error("エラーが発生しました: %s", e)
        raise SystemExit(1) from e


def _run_screen(args: argparse.Namespace) -> None:
    logger.info("JPX銘柄リストを取得中...")
    fetcher = JpxStockListFetcher()
    jpx_data = fetcher.fetch()
    universe = Universe.from_jpx_data(jpx_data)

    if args.test:
        universe = universe.limit(TEST_MODE_LIMIT)
        logger.info("テストモード: %d銘柄に制限", TEST_MODE_LIMIT)

    logger.info("ユニバース: %d銘柄", len(universe))

    cache = None if args.no_cache else FileCache()
    if cache:
        logger.info("キャッシュ有効 (24時間TTL)")
    repo = YFinanceSecurityRepository(cache=cache)
    total = len(universe)
    logger.info("財務データを取得中...")
    for i, sec in enumerate(universe.securities, 1):
        snap = repo.get_financial_snapshot(sec.ticker)
        sec.financial_snapshot = snap
        _print_progress(i, total)

    service = ScreeningService()
    result = service.execute(universe.securities, top_n=args.top)

    _print_result(result)

    if args.output:
        output_path = Path(args.output)
    else:
        today = datetime.now(tz=UTC).strftime("%Y-%m-%d")
        output_path = DEFAULT_DATA_DIR / f"{today}.csv"

    _write_csv(result, output_path)
    logger.info("CSV出力: %s", output_path)


def _print_progress(current: int, total: int) -> None:
    """ターミナルにインラインで進捗を表示する。"""
    pct = current / total * 100
    sys.stderr.write(f"\r  [{current}/{total}] {pct:.0f}%")
    sys.stderr.flush()
    if current == total:
        sys.stderr.write("\n")


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


def _build_eval_provider() -> YFinanceEvaluationDataProvider:
    edinet_api_key = os.environ.get("EDINET_API_KEY")
    if edinet_api_key:
        logger.info("EDINET API キーが設定されています。EdinetEvaluationDataProvider を使用します。")
        client = EdinetClient(api_key=edinet_api_key)
        return EdinetEvaluationDataProvider(edinet_client=client)
    logger.info("EDINET API キー未設定。YFinanceEvaluationDataProvider を使用します。")
    return YFinanceEvaluationDataProvider()


def _run_evaluate(args: argparse.Namespace) -> None:
    input_path = Path(args.input)
    logger.info("スクリーニング結果を読み込み中: %s", input_path)

    with input_path.open(newline="") as f:
        reader = csv.DictReader(f)
        targets = [EvaluationTarget.from_csv_row(row) for row in reader]

    logger.info("評価対象: %d銘柄", len(targets))

    provider = _build_eval_provider()
    service = EvaluationService(provider)
    reports = service.execute(targets)

    _print_evaluation(reports)

    if args.output:
        _write_evaluation_csv(reports, Path(args.output))
        logger.info("評価結果CSV出力: %s", args.output)


def _print_evaluation(reports: list[EvaluationReport]) -> None:
    print(f"\n{'='*80}")
    print("評価結果")
    print(f"{'='*80}")
    print(f"{'順位':>4} {'ティッカー':<10} {'銘柄名':<20} {'判定':<12} {'Gate1':<8} {'Gate2':<8} {'Gate3':<8}")
    print(f"{'-'*80}")
    for r in reports:
        g1 = "PASS" if r.gate1.passed else "FAIL"
        g2 = "PASS" if r.gate2.passed else "FAIL"
        g3 = "PASS" if r.gate3.passed else "FAIL"
        print(
            f"{r.target.discovery_rank:>4} {r.target.ticker.symbol:<10} {r.target.company_name:<20}"
            f" {r.verdict.value.upper():<12} {g1:<8} {g2:<8} {g3:<8}",
        )

    print()
    for r in reports:
        print(f"\n--- {r.target.ticker.symbol} ({r.target.company_name}) ---")
        for gate_result in [r.gate1, r.gate2, r.gate3]:
            print(f"  {gate_result.gate_name}:")
            for c in gate_result.checks:
                mark = {"pass": "o", "fail": "x", "needs_review": "?"}[c.status.value]
                detail = f" ({c.detail})" if c.detail else ""
                print(f"    [{mark}] {c.check_id}: {c.description}{detail}")


def _write_evaluation_csv(reports: list[EvaluationReport], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "rank", "ticker", "company_name", "verdict",
                "gate1", "gate2", "gate3", "score_total",
            ],
        )
        writer.writeheader()
        for r in reports:
            writer.writerow({
                "rank": r.target.discovery_rank,
                "ticker": r.target.ticker.symbol,
                "company_name": r.target.company_name,
                "verdict": r.verdict.value,
                "gate1": "PASS" if r.gate1.passed else "FAIL",
                "gate2": "PASS" if r.gate2.passed else "FAIL",
                "gate3": "PASS" if r.gate3.passed else "FAIL",
                "score_total": r.target.score_total,
            })


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
