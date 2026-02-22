from __future__ import annotations

from datetime import date

from stock_screener.timing.domain.exit_rules import check_exit_conditions
from stock_screener.timing.domain.portfolio import Holding

_ACTIONS_NEEDING_REEVALUATION = {"target_hit", "time_stop"}


def evaluate_holding(
    holding: Holding,
    current_price: float,
    today: date,
) -> dict:
    """exit_rules をラップし、needs_gate_reevaluation フラグを付与する。

    target_hit / time_stop の場合は Gate 再評価が推奨される。
    """
    result = check_exit_conditions(holding, current_price, today)
    result["needs_gate_reevaluation"] = result["action"] in _ACTIONS_NEEDING_REEVALUATION
    return result
