from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from stock_screener.timing.domain.config import LOT_SIZE
from stock_screener.timing.domain.portfolio import Portfolio


def generate_order_sheet(
    entry_results: list[dict],
    exit_results: list[dict],
    portfolio: Portfolio,
    today: date,
    output_dir: str | None = None,
) -> str:
    """エントリー・エグジット結果からオーダーシートを生成する。

    Returns:
        テキスト形式のオーダーシート文字列。
        output_dir 指定時は YYYYMMDD_order.json も出力。
    """
    lines: list[str] = []
    lines.append(f"=== Order Sheet ({today.isoformat()}) ===")
    lines.append(f"Total Capital: {portfolio.total_capital:,.0f}")
    lines.append(f"Cash Balance:  {portfolio.cash_balance:,.0f}")
    lines.append("")

    buy_count = 0
    wait_count = 0
    skip_count = 0

    if entry_results:
        lines.append("--- Entry ---")
        for r in entry_results:
            verdict = r["verdict"]
            ticker = r["ticker"]
            price = r["current_price"]
            score = r.get("signal_score", 0)

            if verdict == "buy":
                buy_count += 1
                required = price * LOT_SIZE
                lines.append(
                    f"  [BUY]  {ticker:<10} price={price:,.0f}  "
                    f"lot={LOT_SIZE}  required={required:,.0f}  score={score}",
                )
            elif verdict == "wait":
                wait_count += 1
                lines.append(f"  [WAIT] {ticker:<10} price={price:,.0f}  score={score}")
            else:
                skip_count += 1
                lines.append(f"  [SKIP] {ticker:<10} {r.get('sizing_message', '')}")
        lines.append("")

    if exit_results:
        lines.append("--- Exit ---")
        for r in exit_results:
            ticker = r["ticker"]
            action = r["action"]
            pnl = r.get("unrealized_pnl", 0)
            pnl_pct = r.get("unrealized_pnl_pct", 0)
            lines.append(
                f"  [{action.upper():<11}] {ticker:<10} "
                f"pnl={pnl:+,.0f} ({pnl_pct:+.1%})",
            )
        lines.append("")

    lines.append(f"Summary: BUY={buy_count} WAIT={wait_count} SKIP={skip_count}")

    text = "\n".join(lines)

    if output_dir is not None:
        _write_json(
            entry_results, exit_results, portfolio, today,
            buy_count, wait_count, skip_count, output_dir,
        )

    return text


def _write_json(
    entry_results: list[dict],
    exit_results: list[dict],
    portfolio: Portfolio,
    today: date,
    buy_count: int,
    wait_count: int,
    skip_count: int,
    output_dir: str,
) -> None:
    dir_path = Path(output_dir)
    dir_path.mkdir(parents=True, exist_ok=True)
    filename = f"{today.strftime('%Y%m%d')}_order.json"
    path = dir_path / filename

    total_required = sum(
        r["current_price"] * LOT_SIZE
        for r in entry_results
        if r["verdict"] == "buy"
    )

    data = {
        "date": today.isoformat(),
        "total_capital": portfolio.total_capital,
        "cash_balance": portfolio.cash_balance,
        "entry_results": entry_results,
        "exit_results": exit_results,
        "summary": {
            "buy_count": buy_count,
            "wait_count": wait_count,
            "skip_count": skip_count,
            "total_required": total_required,
            "remaining_cash": portfolio.cash_balance - total_required,
        },
    }

    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
