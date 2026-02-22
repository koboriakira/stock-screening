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

EVALUATION_CONFIG = {
    "gate1_margin_ratio_max": 5.0,
    "gate2_earnings_growth_min": 0.20,
    "gate2_tob_pbr_max": 1.0,
    "gate2_tob_net_cash_min": 0.30,
    "gate3_net_cash_ratio_min": 0.30,
    "gate3_per_percentile_max": 25.0,
}
