HARD_FILTERS = {
    "market_cap_min": 5_000_000_000,
    "market_cap_max": 50_000_000_000,
    "avg_trading_value_min": 5_000_000,
    "excluded_sectors": ["医薬品", "不動産業"],
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

TURNAROUND_BONUS = 10
