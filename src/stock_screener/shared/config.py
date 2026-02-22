HARD_FILTERS = {
    "market_cap_min": 5_000_000_000,
    "market_cap_max": 50_000_000_000,
    "avg_trading_value_min": 5_000_000,
    "excluded_sectors": [
        "医薬品",
        "不動産業",
        "銀行業",
        "証券、商品先物取引業",
        "保険業",
    ],
    "excluded_categories": [
        "ETF",
        "REIT",
        "ETN",
        "インフラファンド",
    ],
}

SOFT_FILTERS = {
    "per_max": 50,
    "equity_ratio_min": 0.20,
    "revenue_growth_min": -0.30,
}

SCORING_WEIGHTS = {
    "value": 0.4,
    "quality": 0.3,
    "momentum": 0.3,
}

SCORING_MODE = "hybrid"  # "absolute" | "percentile" | "hybrid"
HYBRID_BASE_RATIO = 0.4  # base score ratio (0.0-1.0)

MISSING_DATA_POLICY = "penalty"  # "penalty" | "skip" | "exclude"
MISSING_DATA_EXCLUDE_THRESHOLD = 0.30  # exclude方式の閾値

TURNAROUND_BONUS = 10

# Anomaly detection settings
ANOMALY_IQR_MULTIPLIER = 3.0
ANOMALY_SCORE_CHANGE_THRESHOLD = 20.0
ANOMALY_DOMAIN_RULES: dict[str, dict[str, float]] = {
    "pbr": {"min": 0.05, "max": 50.0},
    "per": {"min": 0.1, "max": 200.0},
    "roe": {"min": -1.0, "max": 1.0},
    "operating_margin": {"min": -1.0, "max": 1.0},
    "equity_ratio": {"min": 0.0, "max": 1.0},
    "dividend_yield": {"min": 0.0, "max": 0.20},
    "net_cash_ratio": {"min": -2.0, "max": 5.0},
}

EVALUATION_CONFIG = {
    "gate1_margin_ratio_max": 5.0,
    "gate2_earnings_growth_min": 0.20,
    "gate2_tob_pbr_max": 1.0,
    "gate2_tob_net_cash_min": 0.30,
    "gate3_net_cash_ratio_min": 0.30,
    "gate3_per_percentile_max": 25.0,
}


def dump_config() -> str:
    """Dump all screening configuration as a human-readable string."""
    lines: list[str] = []
    lines.append("=== Screening Config ===")

    # Hard filters
    lines.append(f"market_cap_min: {HARD_FILTERS['market_cap_min']:,}")
    lines.append(f"market_cap_max: {HARD_FILTERS['market_cap_max']:,}")
    lines.append(f"avg_trading_value_min: {HARD_FILTERS['avg_trading_value_min']:,}")
    lines.append(f"excluded_sectors: {HARD_FILTERS['excluded_sectors']}")
    lines.append(f"excluded_categories: {HARD_FILTERS['excluded_categories']}")

    # Soft filters
    lines.append(f"per_max: {SOFT_FILTERS['per_max']}")
    lines.append(f"equity_ratio_min: {SOFT_FILTERS['equity_ratio_min']}")
    lines.append(f"revenue_growth_min: {SOFT_FILTERS['revenue_growth_min']}")

    # Scoring
    lines.append(f"scoring_mode: {SCORING_MODE}")
    lines.append(f"hybrid_base_ratio: {HYBRID_BASE_RATIO}")
    weights_str = ", ".join(f"{k}={v:.2f}" for k, v in SCORING_WEIGHTS.items())
    lines.append(f"scoring_weights: {weights_str}")

    # Missing data
    lines.append(f"missing_data_policy: {MISSING_DATA_POLICY}")
    lines.append(f"missing_data_exclude_threshold: {MISSING_DATA_EXCLUDE_THRESHOLD}")

    return "\n".join(lines)
