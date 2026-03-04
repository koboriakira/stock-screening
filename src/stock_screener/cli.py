from __future__ import annotations

import argparse
import csv
import logging
import os
import sys
import time
from datetime import UTC, date, datetime
from pathlib import Path

from stock_screener.discovery.domain.anomaly_detector import AnomalyDetector
from stock_screener.discovery.domain.candidate import ScreeningResult
from stock_screener.discovery.domain.diff_report import DiffReport, ScreeningResultSnapshot
from stock_screener.discovery.domain.universe import Universe
from stock_screener.discovery.infrastructure.snapshot_repository import FileSnapshotRepository
from stock_screener.discovery.service import ScreeningService
from stock_screener.evaluation.domain.check import CheckStatus, GateResult
from stock_screener.evaluation.domain.evaluation_report import EvaluationReport
from stock_screener.evaluation.domain.evaluation_target import EvaluationTarget
from stock_screener.evaluation.infrastructure.edinet_client import EdinetClient
from stock_screener.evaluation.infrastructure.edinet_eval_provider import EdinetEvaluationDataProvider
from stock_screener.evaluation.infrastructure.yfinance_eval_provider import YFinanceEvaluationDataProvider
from stock_screener.evaluation.service import EvaluationService
from stock_screener.market_data.domain.security import Security
from stock_screener.market_data.infrastructure.cache import FileCache
from stock_screener.market_data.infrastructure.jpx_stock_list import JpxStockListFetcher
from stock_screener.market_data.infrastructure.yfinance_adapter import YFinanceSecurityRepository
from stock_screener.shared.config import HARD_FILTERS, dump_config

logger = logging.getLogger(__name__)

TEST_MODE_LIMIT = 5
DEFAULT_DATA_DIR = Path.home() / ".local" / "share" / "stock-screener" / "results"


def _build_parser() -> argparse.ArgumentParser:  # noqa: PLR0915
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

    diff_parser = subparsers.add_parser("diff", help="前回との差分レポート")
    diff_parser.add_argument("--top", type=int, default=20, help="上位N銘柄で比較 (default: 20)")

    timing_parser = subparsers.add_parser("timing", help="タイミング&サイジング判定")
    timing_parser.add_argument("--input", type=str, required=True, help="評価結果CSV")
    timing_parser.add_argument("--output-dir", type=str, default=None, help="オーダーシート出力先ディレクトリ")

    monitor_parser = subparsers.add_parser("monitor", help="保有銘柄の日次モニタリング")
    monitor_parser.add_argument("--skip-calendar", action="store_true", help="営業日判定をスキップ")

    buy_parser = subparsers.add_parser("record-buy", help="購入を記録")
    buy_parser.add_argument("--ticker", type=str, required=True, help="銘柄ティッカー (例: 4486.T)")
    buy_parser.add_argument("--price", type=float, required=True, help="購入価格")
    buy_parser.add_argument("--shares", type=int, required=True, help="購入株数")
    buy_parser.add_argument("--date", type=str, required=True, help="購入日 (YYYY-MM-DD)")
    buy_parser.add_argument("--name", type=str, default=None, help="銘柄名 (未指定時は yfinance から取得)")

    sell_parser = subparsers.add_parser("record-sell", help="売却を記録")
    sell_parser.add_argument("--ticker", type=str, required=True, help="銘柄ティッカー")
    sell_parser.add_argument("--price", type=float, required=True, help="売却価格")
    sell_parser.add_argument("--reason", type=str, required=True, help="売却理由")

    trailing_parser = subparsers.add_parser("record-trailing", help="トレイリングストップを適用")
    trailing_parser.add_argument("--ticker", type=str, required=True, help="銘柄ティッカー")

    extension_parser = subparsers.add_parser("record-extension", help="保有期間延長を適用")
    extension_parser.add_argument("--ticker", type=str, required=True, help="銘柄ティッカー")

    sa_save_parser = subparsers.add_parser("save-analysis", help="銘柄分析データを保存")
    sa_save_parser.add_argument("--ticker", type=str, required=True, help="銘柄ティッカー (例: 4486.T)")
    sa_save_parser.add_argument("--file", type=str, required=True, help="分析テキストファイル (.md)")

    sa_show_parser = subparsers.add_parser("show-analysis", help="銘柄分析データを表示")
    sa_show_parser.add_argument("--ticker", type=str, default=None, help="銘柄ティッカー (省略時は全銘柄一覧)")

    wl_add_parser = subparsers.add_parser("watchlist-add", help="ウォッチリストに銘柄を追加")
    wl_add_parser.add_argument("--ticker", type=str, required=True, help="銘柄ティッカー (例: 5765.T)")
    wl_add_parser.add_argument("--name", type=str, required=True, help="銘柄名")
    wl_add_parser.add_argument("--memo", type=str, default="", help="メモ")
    wl_add_parser.add_argument("--score-threshold", type=int, default=None, help="スコア閾値 (デフォルト: 3)")
    wl_add_parser.add_argument("--volume-threshold", type=float, default=None, help="出来高閾値 (デフォルト: 1.5)")
    wl_add_parser.add_argument("--cooldown-days", type=int, default=None, help="通知クールダウン日数 (デフォルト: 3)")

    wl_rm_parser = subparsers.add_parser("watchlist-remove", help="ウォッチリストから銘柄を削除")
    wl_rm_parser.add_argument("--ticker", type=str, required=True, help="銘柄ティッカー")

    subparsers.add_parser("watchlist-list", help="ウォッチリスト一覧を表示")

    wl_check_parser = subparsers.add_parser("watchlist-check", help="ウォッチリスト銘柄の底打ちシグナルをチェック")
    wl_check_parser.add_argument("--dry-run", action="store_true", help="通知を送信せずに結果のみ表示")
    wl_check_parser.add_argument("--output", type=str, default=None, help="JSON レポート出力パス")

    daily_report_parser = subparsers.add_parser("daily-report", help="日次レポートを生成")
    daily_report_parser.add_argument("--skip-calendar", action="store_true", help="営業日判定をスキップ")
    daily_report_parser.add_argument("--notify", action="store_true", help="Slack に通知を送信")

    return parser


def main() -> None:
    """CLI エントリーポイント。"""
    parser = _build_parser()
    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format="%(levelname)s: %(message)s")

    handlers = {
        "screen": _run_screen,
        "evaluate": _run_evaluate,
        "diff": _run_diff,
        "timing": _run_timing,
        "monitor": _run_monitor,
        "record-buy": _run_record_buy,
        "record-sell": _run_record_sell,
        "record-trailing": _run_record_trailing,
        "record-extension": _run_record_extension,
        "save-analysis": _run_save_analysis,
        "show-analysis": _run_show_analysis,
        "watchlist-add": _run_watchlist_add,
        "watchlist-remove": _run_watchlist_remove,
        "watchlist-list": _run_watchlist_list,
        "watchlist-check": _run_watchlist_check,
        "daily-report": _run_daily_report,
    }

    try:
        handler = handlers[args.command]
        handler(args)
    except FileNotFoundError as e:
        logger.error("ファイルが見つかりません: %s", e)
        raise SystemExit(1) from e
    except Exception as e:
        logger.error("エラーが発生しました: %s", e)
        raise SystemExit(1) from e


def _run_screen(args: argparse.Namespace) -> None:
    """Screen subcommand: 2-stage JPX stock screening."""
    logger.info("JPX list fetching...")
    fetcher = JpxStockListFetcher()
    jpx_data = fetcher.fetch()
    universe = Universe.from_jpx_data(jpx_data)

    if args.test:
        universe = universe.limit(TEST_MODE_LIMIT)
        logger.info("Test mode: %d stocks", TEST_MODE_LIMIT)

    logger.info("Universe: %d stocks", len(universe))

    cache = None if args.no_cache else FileCache()
    if cache:
        logger.info("Cache enabled (24h TTL)")
    repo = YFinanceSecurityRepository(cache=cache)

    # Stage 1: sector/category pre-filter + market cap only
    stage2_candidates = _stage1_filter(universe.securities, repo)

    # Stage 2: full data fetch for filtered stocks
    _stage2_fetch(stage2_candidates, repo)

    service = ScreeningService()
    result = service.execute(stage2_candidates, top_n=args.top)

    # Anomaly detection
    snap_repo = FileSnapshotRepository()
    previous = snap_repo.load_latest()
    universe_snaps = [s.financial_snapshot for s in stage2_candidates]
    detector = AnomalyDetector()
    anomaly_flags = detector.detect_all(result.candidates, universe_snaps, previous)
    result = ScreeningResult(
        candidates=result.candidates,
        total_universe=result.total_universe,
        after_hard_filter=result.after_hard_filter,
        after_soft_filter=result.after_soft_filter,
        timestamp=result.timestamp,
        anomaly_flags=anomaly_flags,
    )
    if anomaly_flags:
        logger.info("Anomaly flags: %d stocks", len(anomaly_flags))

    _print_result(result)

    output_path = Path(args.output) if args.output else _default_output_path()
    _write_csv(result, output_path)
    logger.info("CSV: %s", output_path)

    # Save snapshot for diff
    snapshot = ScreeningResultSnapshot.from_screening_result(result)
    snap_path = snap_repo.save(snapshot)
    logger.info("Snapshot: %s", snap_path)


def _default_output_path() -> Path:
    """Generate default output path with today's date."""
    today = datetime.now(tz=UTC).strftime("%Y-%m-%d")
    return DEFAULT_DATA_DIR / f"{today}.csv"


def _stage1_filter(
    securities: list[Security],
    repo: YFinanceSecurityRepository,
) -> list[Security]:
    """Stage 1: Lightweight pre-filter by sector/category, then market cap."""
    excluded_sectors = set(HARD_FILTERS["excluded_sectors"])
    excluded_categories = HARD_FILTERS["excluded_categories"]

    pre_filtered = [
        sec
        for sec in securities
        if sec.sector not in excluded_sectors
        and not (sec.market and any(cat in sec.market for cat in excluded_categories))
    ]
    logger.info("Stage 1 pre-filter: %d -> %d (sector/category)", len(securities), len(pre_filtered))

    mcap_min = HARD_FILTERS["market_cap_min"]
    mcap_max = HARD_FILTERS["market_cap_max"]
    total = len(pre_filtered)
    logger.info("Stage 1: fetching market cap for %d stocks...", total)
    start_time = time.monotonic()

    passed = []
    for i, sec in enumerate(pre_filtered, 1):
        mcap = repo.get_market_cap_only(sec.ticker)
        _print_progress(i, total, start_time, sec.ticker.symbol)
        if mcap is not None and mcap_min <= mcap <= mcap_max:
            passed.append(sec)

    logger.info("Stage 1 done: %d stocks passed market cap filter", len(passed))
    return passed


def _stage2_fetch(
    candidates: list[Security],
    repo: YFinanceSecurityRepository,
) -> None:
    """Stage 2: Fetch full financial data for filtered stocks."""
    total = len(candidates)
    logger.info("Stage 2: fetching full data for %d stocks...", total)
    start_time = time.monotonic()

    for i, sec in enumerate(candidates, 1):
        snap = repo.get_financial_snapshot(sec.ticker)
        sec.financial_snapshot = snap
        _print_progress(i, total, start_time, sec.ticker.symbol)


def _print_progress(
    current: int,
    total: int,
    start_time: float,
    ticker: str = "",
) -> None:
    """ターミナルにインラインで進捗を表示する。"""
    pct = current / total * 100
    elapsed = time.monotonic() - start_time

    if current > 1 and elapsed > 0:
        avg_per_item = elapsed / current
        remaining = avg_per_item * (total - current)
        eta_str = _format_duration(remaining)
    else:
        eta_str = "--:--"

    elapsed_str = _format_duration(elapsed)
    ticker_display = f" {ticker:<10}" if ticker else ""
    sys.stderr.write(f"\r  [{current}/{total}] {pct:3.0f}%{ticker_display} 経過{elapsed_str} 残{eta_str}")
    sys.stderr.flush()
    if current == total:
        sys.stderr.write("\n")


def _format_duration(seconds: float) -> str:
    """秒数を MM:SS 形式に変換する。"""
    minutes = int(seconds) // 60
    secs = int(seconds) % 60
    return f"{minutes:02d}:{secs:02d}"


def _format_anomaly_flags(flags: list) -> str:
    """Format anomaly flags as a CSV-safe string."""
    if not flags:
        return ""
    return "; ".join(f"[{f.rule}:{f.field}={f.value}]" for f in flags)


def _fmt_oku(market_cap: float | None) -> str:
    """Format market cap in oku-yen."""
    if market_cap is None:
        return "-"
    return f"{market_cap / 100_000_000:.0f}"


def _fmt_pct(value: float | None) -> str:
    """Format a ratio as percentage."""
    if value is None:
        return "-"
    return f"{value * 100:.1f}"


def _fmt_f(value: float | None) -> str:
    """Format float, '-' for None."""
    if value is None:
        return "-"
    return f"{value:.1f}"


def _print_result(result: ScreeningResult) -> None:
    """Print screening results in tabular format with extended columns."""
    width = 140
    print(f"\n{dump_config()}")
    print(f"\n{'=' * width}")
    print(f"Screening ({result.timestamp.strftime('%Y-%m-%d %H:%M')} UTC)")
    print(
        f"Universe: {result.total_universe} -> Hard: {result.after_hard_filter} -> Soft: {result.after_soft_filter}",
    )
    print(f"{'=' * width}")
    header = (
        f"{'#':>3} {'Ticker':<10} {'Name':<16} {'Sector':<8}"
        f" {'MCap':>5} {'Total':>5} {'Val':>5} {'Qual':>5} {'Mom':>5}"
        f" {'PER':>6} {'PBR':>5} {'DivY':>5} {'NC%':>5}"
    )
    print(header)
    print(f"{'-' * width}")
    for c in result.candidates:
        snap = c.security.financial_snapshot
        sector_short = c.security.sector[:8] if c.security.sector else ""
        line = (
            f"{c.rank:>3} {c.security.ticker.symbol:<10} {c.security.company_name:<16}"
            f" {sector_short:<8}"
            f" {_fmt_oku(snap.market_cap):>5}"
            f" {c.score.total:>5.1f} {c.score.value:>5.1f}"
            f" {c.score.quality:>5.1f} {c.score.momentum:>5.1f}"
            f" {_fmt_f(snap.per):>6} {_fmt_f(snap.pbr):>5}"
            f" {_fmt_pct(snap.dividend_yield):>5} {_fmt_pct(snap.net_cash_ratio):>5}"
        )
        if snap.data_completeness < 0.7:
            line += f"  [!] {snap.data_completeness:.0%}"
        ticker_flags = result.anomaly_flags.get(c.security.ticker.symbol, [])
        if ticker_flags:
            flag_fields = ", ".join(f.field for f in ticker_flags)
            line += f"  [W] {flag_fields}"
        print(line)
    print()


def _build_eval_provider() -> YFinanceEvaluationDataProvider:
    """環境変数に基づいて評価データプロバイダを構築する。

    EDINET_API_KEY が設定されている場合は EdinetEvaluationDataProvider、
    未設定の場合は YFinanceEvaluationDataProvider を返す。
    """
    edinet_api_key = os.environ.get("EDINET_API_KEY")
    if edinet_api_key:
        logger.info("EDINET API キーが設定されています。EdinetEvaluationDataProvider を使用します。")
        client = EdinetClient(api_key=edinet_api_key)
        return EdinetEvaluationDataProvider(edinet_client=client)
    logger.info("EDINET API キー未設定。YFinanceEvaluationDataProvider を使用します。")
    return YFinanceEvaluationDataProvider()


def _run_evaluate(args: argparse.Namespace) -> None:
    """evaluate サブコマンド: スクリーニング結果を 3-Gate パイプラインで評価する。"""
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
        output_path = Path(args.output)
        _write_evaluation_csv(reports, output_path)
        logger.info("評価結果CSV出力: %s", output_path)
        detail_path = output_path.with_name(f"{output_path.stem}_detail{output_path.suffix}")
        _write_evaluation_detail_csv(reports, detail_path)
        logger.info("評価詳細CSV出力: %s", detail_path)


def _run_diff(args: argparse.Namespace) -> None:
    """diff subcommand: compare latest screening result with previous."""
    snap_repo = FileSnapshotRepository()
    latest = snap_repo.load_latest()
    if latest is None:
        logger.error("No snapshot found. Run 'screen' first.")
        raise SystemExit(1)

    previous = snap_repo.load_previous()
    if previous is None:
        logger.error("Only one snapshot found. Need at least two for diff.")
        raise SystemExit(1)

    diff = DiffReport.compare(previous, latest, top_n=args.top)
    print(diff.format())


def _gate_stats_str(gate_result: GateResult) -> str:
    """GateResult のチェック統計を文字列化する。"""
    pass_count = sum(1 for c in gate_result.checks if c.status == CheckStatus.PASS)
    fail_count = sum(1 for c in gate_result.checks if c.status == CheckStatus.FAIL)
    review_count = sum(1 for c in gate_result.checks if c.status == CheckStatus.NEEDS_REVIEW)
    total = len(gate_result.checks)
    parts = []
    if pass_count:
        parts.append(f"o{pass_count}")
    if fail_count:
        parts.append(f"x{fail_count}")
    if review_count:
        parts.append(f"?{review_count}")
    return f"{'PASS' if gate_result.passed else 'FAIL'} ({'/'.join(parts)}/{total})"


def _print_evaluation(reports: list[EvaluationReport]) -> None:
    """評価結果をターミナルに一覧表と詳細で出力する。"""
    print(f"\n{'=' * 80}")
    print("評価結果")
    print(f"{'=' * 80}")
    print(f"{'順位':>4} {'ティッカー':<10} {'銘柄名':<20} {'判定':<12} {'Gate1':<8} {'Gate2':<8} {'Gate3':<8}")
    print(f"{'-' * 80}")
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
        print(f"  判定: {r.verdict.value.upper()}")
        if r.verdict_reason:
            print(f"  理由: {r.verdict_reason}")
        for gate_result in [r.gate1, r.gate2, r.gate3]:
            stats = _gate_stats_str(gate_result)
            review_count = sum(
                1 for c in gate_result.checks
                if c.status.value == "needs_review"
            )
            review_note = f" | 要確認: {review_count}件" if review_count else ""
            print(f"  {gate_result.gate_name}: {stats}{review_note}")
            for c in gate_result.checks:
                mark = {"pass": "o", "fail": "x", "needs_review": "?"}[c.status.value]
                detail = f" ({c.detail})" if c.detail else ""
                print(f"    [{mark}] {c.check_id}: {c.description}{detail}")


def _write_evaluation_csv(reports: list[EvaluationReport], path: Path) -> None:
    """評価結果を CSV ファイルに出力する。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "rank",
                "ticker",
                "company_name",
                "verdict",
                "gate1",
                "gate2",
                "gate3",
                "score_total",
            ],
        )
        writer.writeheader()
        for r in reports:
            writer.writerow(
                {
                    "rank": r.target.discovery_rank,
                    "ticker": r.target.ticker.symbol,
                    "company_name": r.target.company_name,
                    "verdict": r.verdict.value,
                    "gate1": "PASS" if r.gate1.passed else "FAIL",
                    "gate2": "PASS" if r.gate2.passed else "FAIL",
                    "gate3": "PASS" if r.gate3.passed else "FAIL",
                    "score_total": r.target.score_total,
                },
            )


_DETAIL_CSV_FIELDNAMES = [
    "rank",
    "ticker",
    "company_name",
    "sector",
    "verdict",
    "score_total",
    "gate",
    "check_id",
    "check_status",
    "check_description",
    "check_detail",
]


def _write_evaluation_detail_csv(reports: list[EvaluationReport], path: Path) -> None:
    """評価結果を縦展開(1行1チェック)の詳細CSVファイルに出力する。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=_DETAIL_CSV_FIELDNAMES)
        writer.writeheader()
        for r in reports:
            base = {
                "rank": r.target.discovery_rank,
                "ticker": r.target.ticker.symbol,
                "company_name": r.target.company_name,
                "sector": r.target.sector,
                "verdict": r.verdict.value,
                "score_total": r.target.score_total,
            }
            for gate_result in [r.gate1, r.gate2, r.gate3]:
                gate_label = gate_result.gate_name.split(":")[0].strip()
                for c in gate_result.checks:
                    writer.writerow(
                        {
                            **base,
                            "gate": gate_label,
                            "check_id": c.check_id,
                            "check_status": c.status.value,
                            "check_description": c.description,
                            "check_detail": c.detail or "",
                        },
                    )


_CSV_FIELDNAMES = [
    "rank",
    "ticker",
    "company_name",
    "sector",
    "market_cap",
    "total_score",
    "value_score",
    "quality_score",
    "momentum_score",
    "per",
    "pbr",
    "roe",
    "operating_margin",
    "equity_ratio",
    "revenue_growth",
    "op_profit_growth",
    "dividend_yield",
    "net_cash_ratio",
    "week52_high_discount",
    "current_price",
    "data_completeness",
    "missing_fields",
    "anomaly_flags",
    "screening_date",
]


def _write_csv(result: ScreeningResult, path: Path) -> None:
    """Write screening results to CSV with full financial data."""
    path.parent.mkdir(parents=True, exist_ok=True)
    screening_date = result.timestamp.strftime("%Y-%m-%d")

    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=_CSV_FIELDNAMES)
        writer.writeheader()
        for c in result.candidates:
            snap = c.security.financial_snapshot
            writer.writerow(
                {
                    "rank": c.rank,
                    "ticker": c.security.ticker.symbol,
                    "company_name": c.security.company_name,
                    "sector": c.security.sector,
                    "market_cap": snap.market_cap,
                    "total_score": round(c.score.total, 2),
                    "value_score": round(c.score.value, 2),
                    "quality_score": round(c.score.quality, 2),
                    "momentum_score": round(c.score.momentum, 2),
                    "per": snap.per,
                    "pbr": snap.pbr,
                    "roe": snap.roe,
                    "operating_margin": snap.operating_margin,
                    "equity_ratio": snap.equity_ratio,
                    "revenue_growth": snap.revenue_growth,
                    "op_profit_growth": snap.operating_profit_growth,
                    "dividend_yield": snap.dividend_yield,
                    "net_cash_ratio": snap.net_cash_ratio,
                    "week52_high_discount": snap.high_52w_discount,
                    "current_price": snap.current_price,
                    "data_completeness": round(snap.data_completeness, 2),
                    "missing_fields": ",".join(snap.missing_fields),
                    "anomaly_flags": _format_anomaly_flags(
                        result.anomaly_flags.get(c.security.ticker.symbol, []),
                    ),
                    "screening_date": screening_date,
                },
            )


def _run_timing(args: argparse.Namespace) -> None:
    """timing サブコマンド: タイミング&サイジング判定を実行する。"""
    from stock_screener.timing.service import TimingService  # noqa: PLC0415

    logger.info("タイミング判定を開始: %s", args.input)
    service = TimingService()
    text = service.execute(
        eval_csv_path=args.input,
        output_dir=args.output_dir,
    )
    print(text)


def _run_monitor(args: argparse.Namespace) -> None:
    """monitor サブコマンド: 保有銘柄の日次モニタリングを実行する。"""
    from stock_screener.monitoring.service import DailyMonitoringService  # noqa: PLC0415

    logger.info("日次モニタリングを開始")
    service = DailyMonitoringService()
    result = service.execute(skip_calendar=args.skip_calendar)

    if result["skipped"]:
        print(f"スキップ: {result['reason']}")
        return

    print(f"モニタリング結果 ({result['date']})")
    print(f"  対象銘柄数: {len(result['results'])}")
    print(f"  通知送信数: {result['notifications_sent']}")
    if result["report_path"]:
        print(f"  レポート: {result['report_path']}")

    for r in result["results"]:
        action = r["action"]
        ticker = r["ticker"]
        pnl_pct = r.get("unrealized_pnl_pct", 0)
        print(f"  {ticker}: {action} ({pnl_pct:+.1%})")

    analysis_alerts = result.get("analysis_alerts", [])
    if analysis_alerts:
        print(f"\n  分析アラート: {len(analysis_alerts)}件")
        for alert in analysis_alerts:
            _type = alert["type"]
            ticker = alert["ticker"]
            if _type == "support_approach":
                lvl = alert["level"]
                print(f"    [サポート接近] {ticker}: {lvl['price']:,.0f} ({lvl['label']})")
            elif _type == "resistance_approach":
                lvl = alert["level"]
                print(f"    [レジスタンス接近] {ticker}: {lvl['price']:,.0f} ({lvl['label']})")
            elif _type == "key_date_approaching":
                sev = {"high": "!!!", "medium": "!!", "low": "!"}.get(alert["severity"], "")
                print(f"    [重要日{sev}] {ticker}: {alert['event']}")


def _run_record_buy(args: argparse.Namespace) -> None:
    """record-buy サブコマンド: 購入を記録する。"""
    from stock_screener.monitoring.domain.portfolio_updater import record_buy  # noqa: PLC0415
    from stock_screener.timing.infrastructure.portfolio_repository import PortfolioRepository  # noqa: PLC0415

    repo = PortfolioRepository()
    portfolio = repo.load()

    buy_date = date.fromisoformat(args.date)

    name = args.name
    if name is None:
        import yfinance as yf  # noqa: PLC0415

        logger.info("銘柄名を yfinance から取得中: %s", args.ticker)
        info = yf.Ticker(args.ticker).info
        name = info.get("shortName") or info.get("longName") or args.ticker

    updated = record_buy(
        portfolio,
        ticker=args.ticker,
        name=name,
        price=args.price,
        shares=args.shares,
        buy_date=buy_date,
    )
    repo.save(updated)

    holding = updated.find_holding(args.ticker)
    print(f"購入記録完了: {args.ticker} ({name})")
    print(f"  価格: {args.price:.0f} x {args.shares}株 = {args.price * args.shares:,.0f}円")
    print(f"  損切り: {holding.stop_loss:,.0f}  利確: {holding.target_price:,.0f}")
    print(f"  最大保有日: {holding.max_holding_date}")
    print(f"  残り現金: {updated.cash_balance:,.0f}円")


def _run_record_sell(args: argparse.Namespace) -> None:
    """record-sell サブコマンド: 売却を記録する。"""
    from stock_screener.monitoring.domain.portfolio_updater import record_sell  # noqa: PLC0415
    from stock_screener.timing.infrastructure.portfolio_repository import PortfolioRepository  # noqa: PLC0415

    repo = PortfolioRepository()
    portfolio = repo.load()

    import datetime as _dt  # noqa: PLC0415

    today = _dt.datetime.now(tz=_dt.UTC).date()
    updated = record_sell(portfolio, args.ticker, args.price, today, args.reason)
    repo.save(updated)
    logger.info("売却記録: %s @ %.0f (%s)", args.ticker, args.price, args.reason)
    print(f"売却記録完了: {args.ticker} @ {args.price:.0f} ({args.reason})")


def _run_record_trailing(args: argparse.Namespace) -> None:
    """record-trailing サブコマンド: トレイリングストップを適用する。"""
    from stock_screener.monitoring.domain.portfolio_updater import apply_trailing_stop  # noqa: PLC0415
    from stock_screener.timing.infrastructure.portfolio_repository import PortfolioRepository  # noqa: PLC0415

    repo = PortfolioRepository()
    portfolio = repo.load()
    updated = apply_trailing_stop(portfolio, args.ticker)
    repo.save(updated)
    h = updated.find_holding(args.ticker)
    logger.info("トレイリング適用: %s (count=%d, target=%.0f)", args.ticker, h.trailing_count, h.target_price)
    print(f"トレイリング適用: {args.ticker} (回数={h.trailing_count}, 新目標値={h.target_price:.0f})")


def _run_save_analysis(args: argparse.Namespace) -> None:
    """save-analysis サブコマンド: 分析テキストを保存し、構造化JSONを生成する。"""
    from stock_screener.monitoring.domain.analysis import AnalysisData  # noqa: PLC0415
    from stock_screener.monitoring.infrastructure.analysis_repository import AnalysisRepository  # noqa: PLC0415

    repo = AnalysisRepository()
    md_path = Path(args.file)
    if not md_path.exists():
        logger.error("ファイルが見つかりません: %s", md_path)
        raise SystemExit(1)

    md_text = md_path.read_text(encoding="utf-8")
    saved_md = repo.save_markdown(args.ticker, md_text)
    print(f"分析テキスト保存: {saved_md}")

    existing = repo.load(args.ticker)
    if existing is None:
        today = datetime.now(tz=UTC).date()
        template = AnalysisData(
            ticker=args.ticker,
            updated_at=today,
            thesis="（要記入）",
        )
        saved_json = repo.save(template)
        print(f"JSON テンプレート生成: {saved_json}")
        print("  → サポート/レジスタンス、重要日、カタリスト、リスクを編集してください")
    else:
        print(f"既存 JSON あり (更新日: {existing.updated_at})")
        print("  → JSON を直接編集して分析データを更新できます")


def _run_show_analysis(args: argparse.Namespace) -> None:
    """show-analysis サブコマンド: 銘柄分析データを表示する。"""
    from stock_screener.monitoring.infrastructure.analysis_repository import AnalysisRepository  # noqa: PLC0415

    repo = AnalysisRepository()

    if args.ticker is None:
        _show_analysis_list(repo)
    else:
        analysis = repo.load(args.ticker)
        if analysis is None:
            print(f"分析データなし: {args.ticker}")
        else:
            _print_analysis_detail(analysis)


def _show_analysis_list(repo) -> None:  # noqa: ANN001
    tickers = repo.list_tickers()
    if not tickers:
        print("分析データなし")
        return
    print("保存済み分析データ:")
    for t in tickers:
        a = repo.load(t)
        print(f"  {t}: {a.thesis} (更新: {a.updated_at})")


def _print_analysis_detail(analysis) -> None:  # noqa: ANN001, C901
    from stock_screener.monitoring.domain.analysis import KeyDate, KeyDateRange  # noqa: PLC0415

    today = datetime.now(tz=UTC).date()
    print(f"=== {analysis.ticker} ===")
    print(f"テーゼ: {analysis.thesis}")
    print(f"更新日: {analysis.updated_at}")

    if analysis.supports or analysis.resistances:
        print("\n[プライスレベル]")
        for s in sorted(analysis.supports, key=lambda x: x.price, reverse=True):
            print(f"  S {s.price:,.0f}  {s.label}")
        for r in sorted(analysis.resistances, key=lambda x: x.price):
            print(f"  R {r.price:,.0f}  {r.label}")

    if analysis.key_dates:
        print("\n[重要日]")
        for kd in analysis.key_dates:
            severity_mark = {"high": "!!!", "medium": "!!", "low": "!"}.get(kd.severity, "")
            if isinstance(kd, KeyDateRange):
                in_range = kd.start <= today <= kd.end
                status = " ← 期間中" if in_range else ""
                print(f"  {kd.start} 〜 {kd.end}  {kd.event} {severity_mark}{status}")
            elif isinstance(kd, KeyDate):
                days_until = (kd.date - today).days
                status = f" ({days_until}日後)" if days_until >= 0 else " (経過済み)"
                print(f"  {kd.date}  {kd.event} {severity_mark}{status}")

    if analysis.catalysts:
        print("\n[カタリスト]")
        for c in analysis.catalysts:
            print(f"  {c.id}: {c.description} ({c.timing}) [影響:{c.impact} 確率:{c.probability}]")

    if analysis.risks:
        print("\n[リスク]")
        for r in analysis.risks:
            print(f"  {r.id}: {r.description} ({r.timing}) [影響:{r.impact} 確率:{r.probability}]")


def _run_record_extension(args: argparse.Namespace) -> None:
    """record-extension サブコマンド: 保有期間延長を適用する。"""
    from stock_screener.monitoring.domain.portfolio_updater import apply_time_extension  # noqa: PLC0415
    from stock_screener.timing.infrastructure.portfolio_repository import PortfolioRepository  # noqa: PLC0415

    repo = PortfolioRepository()
    portfolio = repo.load()
    updated = apply_time_extension(portfolio, args.ticker)
    repo.save(updated)
    h = updated.find_holding(args.ticker)
    logger.info("保有期間延長: %s (count=%d, max_date=%s)", args.ticker, h.extension_count, h.max_holding_date)
    print(f"保有期間延長: {args.ticker} (回数={h.extension_count}, 新期限={h.max_holding_date})")


def _run_watchlist_add(args: argparse.Namespace) -> None:
    """watchlist-add サブコマンド: ウォッチリストに銘柄を追加する。"""
    from stock_screener.monitoring.domain.watchlist import WatchlistParams  # noqa: PLC0415
    from stock_screener.monitoring.watchlist_service import WatchlistMonitoringService  # noqa: PLC0415

    service = WatchlistMonitoringService()
    params_kwargs = {}
    if args.score_threshold is not None:
        params_kwargs["score_threshold"] = args.score_threshold
    if args.volume_threshold is not None:
        params_kwargs["volume_threshold"] = args.volume_threshold
    if args.cooldown_days is not None:
        params_kwargs["cooldown_days"] = args.cooldown_days

    params = WatchlistParams(**params_kwargs) if params_kwargs else None

    entry = service.add_entry(
        ticker=args.ticker,
        name=args.name,
        memo=args.memo,
        params=params,
    )
    price_str = f" @ {entry.registered_price:,.0f}" if entry.registered_price else ""
    print(f"ウォッチリストに追加: {args.ticker} ({args.name}){price_str}")


def _run_watchlist_remove(args: argparse.Namespace) -> None:
    """watchlist-remove サブコマンド: ウォッチリストから銘柄を削除する。"""
    from stock_screener.monitoring.infrastructure.watchlist_repository import WatchlistRepository  # noqa: PLC0415

    repo = WatchlistRepository()
    wl = repo.load()
    wl.remove(args.ticker)
    repo.save(wl)
    print(f"ウォッチリストから削除: {args.ticker}")


def _run_watchlist_list(args: argparse.Namespace) -> None:  # noqa: ARG001
    """watchlist-list サブコマンド: ウォッチリスト一覧を表示する。"""
    from stock_screener.monitoring.infrastructure.watchlist_repository import WatchlistRepository  # noqa: PLC0415

    repo = WatchlistRepository()
    wl = repo.load()
    if not wl.entries:
        print("ウォッチリストは空です")
        return

    print(f"\nウォッチリスト ({len(wl.entries)} 銘柄)")
    print(
        f"{'Ticker':<12} {'Name':<16} {'Added':<12} {'RegPrice':>8} "
        f"{'Score':>5} {'CD':>3} {'Memo'}",
    )
    print("-" * 80)
    for e in wl.entries:
        reg_price = f"{e.registered_price:,.0f}" if e.registered_price else "-"
        last_score = str(e.score_history[-1].score) if e.score_history else "-"
        cd_days = str(e.params.cooldown_days)
        print(
            f"{e.ticker:<12} {e.name:<16} {e.added_date.isoformat():<12} {reg_price:>8} "
            f"{last_score:>5} {cd_days:>3} {e.memo}",
        )


def _run_watchlist_check(args: argparse.Namespace) -> None:
    """watchlist-check サブコマンド: 底打ちシグナルをチェックする。"""
    from stock_screener.monitoring.watchlist_service import WatchlistMonitoringService  # noqa: PLC0415

    logger.info("ウォッチリスト シグナルチェックを開始")
    service = WatchlistMonitoringService()

    output_path = Path(args.output) if args.output else None
    results = service.execute(dry_run=args.dry_run, output_path=output_path)

    if not results:
        print("ウォッチリストが空か、データ取得に失敗しました")
        return

    if args.dry_run:
        print("[dry-run] 通知は送信されません")

    print(f"\nウォッチリスト シグナルチェック ({len(results)} 銘柄)")
    print(
        f"{'Ticker':<12} {'Name':<16} {'Score':>5} {'Delta':>5} "
        f"{'Price':>8} {'Chg%':>6} {'Level':<14} {'CD':>3} {'Notif':>5}",
    )
    print("-" * 100)
    for r in results:
        sig = r["signal"]
        level_str = sig.level or "-"
        delta_str = _fmt_delta(sig.score_delta)
        price_str = f"{r['current_price']:,.0f}" if r["current_price"] else "-"
        chg_str = f"{r['price_change_pct'] * 100:+.1f}" if r["price_change_pct"] is not None else "-"
        notif_str = "o" if r["notified"] else "x"
        cd_str = str(r["cooldown_remaining_days"])
        print(
            f"{r['ticker']:<12} {r['name']:<16} {sig.score:>3}/{sig.max_score} {delta_str:>5} "
            f"{price_str:>8} {chg_str:>6} {level_str:<14} {cd_str:>3} {notif_str:>5}",
        )

    if output_path:
        print(f"\nJSON: {output_path}")


def _run_daily_report(args: argparse.Namespace) -> None:
    """daily-report サブコマンド: 日次レポートを生成し、オプションで Slack に通知する。"""
    from stock_screener.monitoring.domain.daily_summary import format_daily_summary  # noqa: PLC0415
    from stock_screener.monitoring.infrastructure.slack_notifier import send_notification  # noqa: PLC0415
    from stock_screener.monitoring.service import DailyMonitoringService  # noqa: PLC0415
    from stock_screener.monitoring.watchlist_service import WatchlistMonitoringService  # noqa: PLC0415

    today = datetime.now(tz=UTC).date()

    # 1. 保有銘柄モニタリング
    logger.info("日次レポート: 保有銘柄モニタリング開始")
    monitor_service = DailyMonitoringService()
    monitor_result = monitor_service.execute(
        today=today,
        skip_calendar=args.skip_calendar,
    )

    if monitor_result["skipped"]:
        print(f"スキップ: {monitor_result['reason']}")
        return

    # 2. ウォッチリストチェック
    logger.info("日次レポート: ウォッチリストチェック開始")
    watchlist_service = WatchlistMonitoringService()
    watchlist_results = watchlist_service.execute()

    # 3. サマリー生成
    summary = format_daily_summary(
        monitor_results=monitor_result["results"],
        watchlist_results=watchlist_results,
        today=today,
        analysis_alerts=monitor_result.get("analysis_alerts", []),
    )

    print(summary)

    # 4. Slack 通知
    if args.notify:
        if send_notification(summary):
            logger.info("Slack 通知送信完了")
        else:
            logger.warning("Slack 通知送信失敗")


def _fmt_delta(delta: int | None) -> str:
    if delta is None:
        return "-"
    return f"+{delta}" if delta >= 0 else str(delta)
