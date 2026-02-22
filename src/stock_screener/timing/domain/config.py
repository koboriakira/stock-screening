"""Layer 5: Timing & Sizing パラメータ定数"""

# === サイジング ===
LOT_SIZE: int = 100
MAX_CONCENTRATION: float = 0.50
MIN_CASH_RESERVE: float = 0.10

# === ブロッカー条件 ===
EARNINGS_BLACKOUT_DAYS: int = 5
MIN_AVG_VOLUME_5D: int = 500

# === シグナル条件 ===
SIGNAL_THRESHOLD: int = 2
MA_PERIOD: int = 25
MA_TOLERANCE: float = 1.05
POST_EARNINGS_MIN_DAYS: int = 3
POST_EARNINGS_MAX_DAYS: int = 20
DIVIDEND_RECORD_MIN_DAYS: int = 30
DIVIDEND_RECORD_MAX_DAYS: int = 90

# === エグジット ===
STOP_LOSS_PCT: float = 0.15
TARGET_GAIN_PCT: float = 0.50
TRAILING_STEP_PCT: float = 0.25
MAX_HOLDING_DAYS: int = 180
EXTENSION_DAYS: int = 90
