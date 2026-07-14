"""
Centralized configuration for the W-pattern stock screener.
All tunable parameters live here.
"""

# =============================================================================
# PATHS
# =============================================================================

from pathlib import Path
from datetime import datetime

current_date = datetime.now()

MONTH = current_date.strftime("%b").lower()
DAY = current_date.strftime("%d")
YEAR = str(current_date.year)

DATA_DIR = Path("./data")

CHARTS_DIR = DATA_DIR / f"charts/{YEAR}/{MONTH}/{DAY}"
CACHE_FILE = CHARTS_DIR / "ohlcv_cache.parquet"
RESULTS_FILE = CHARTS_DIR / "screener_results.csv"

# Create directory if DNE
CHARTS_DIR.mkdir(parents=True, exist_ok=True)


# =============================================================================
# UNIVERSE FILTERS
# =============================================================================
MIN_MARKET_CAP = 300_000_000        # $300mm minimum
MIN_AVG_VOLUME_60D = 500_000        # 500k shares average daily volume
LOOKBACK_YEARS = 2                  # Years of historical data to fetch

# =============================================================================
# PATTERN DETECTION WINDOWS
# =============================================================================
TRAILING_WINDOWS = [40, 55, 75, 100, 130]  # Bars to analyze
MIN_LEG_BARS = 5                            # Minimum bars per leg
PIVOT_ORDER = 3                             # Neighborhood for local extrema

# =============================================================================
# SHAPE SCORE WEIGHTS (must sum to 1.0)
# =============================================================================
WEIGHTS = {
    "slope_conviction": 0.26,    # Directional slope strength
    "straightness": 0.26,        # R² of leg fits
    "leg_balance": 0.15,         # Symmetry of leg lengths
    "nearness_to_low": 0.13,     # Current price near first low
    "bounce_amplitude": 0.12,    # Bounce vs leg-1 drop
    "drop_depth": 0.08,          # Depth of initial decline
}

# =============================================================================
# QUALITY GATE
# =============================================================================
DEFAULT_RESIDUAL_TOLERANCE = 4.0   # Max residual std as % of price
RESIDUAL_TOLERANCE_RANGE = (0.5, 12.0)  # Slider bounds

# =============================================================================
# RELAXATION LEVELS (strict → loose)
# Each level defines hard gates that must be passed
# =============================================================================
RELAXATION_LEVELS = [
    {   # Level 0: Strictest
        "name": "Strict",
        "min_mean_r2": 0.85,
        "min_weakest_r2": 0.75,
        "min_abs_slope_pct": 0.15,    # Min |slope| per bar as %
        "max_nearness_pct": 3.0,      # Current price within X% of first low
        "min_bounce_retrace": 0.40,   # Bounce retraces at least 40% of leg1
        "min_leg1_drop_pct": 8.0,     # Leg 1 must drop at least 8%
        "min_leg_balance": 0.5,       # Shortest leg >= 50% of longest
    },
    {   # Level 1
        "name": "Firm",
        "min_mean_r2": 0.78,
        "min_weakest_r2": 0.65,
        "min_abs_slope_pct": 0.12,
        "max_nearness_pct": 5.0,
        "min_bounce_retrace": 0.33,
        "min_leg1_drop_pct": 6.0,
        "min_leg_balance": 0.4,
    },
    {   # Level 2
        "name": "Moderate",
        "min_mean_r2": 0.70,
        "min_weakest_r2": 0.55,
        "min_abs_slope_pct": 0.08,
        "max_nearness_pct": 7.0,
        "min_bounce_retrace": 0.25,
        "min_leg1_drop_pct": 5.0,
        "min_leg_balance": 0.33,
    },
    {   # Level 3
        "name": "Relaxed",
        "min_mean_r2": 0.60,
        "min_weakest_r2": 0.45,
        "min_abs_slope_pct": 0.05,
        "max_nearness_pct": 10.0,
        "min_bounce_retrace": 0.20,
        "min_leg1_drop_pct": 4.0,
        "min_leg_balance": 0.25,
    },
    {   # Level 4
        "name": "Loose",
        "min_mean_r2": 0.50,
        "min_weakest_r2": 0.35,
        "min_abs_slope_pct": 0.03,
        "max_nearness_pct": 12.0,
        "min_bounce_retrace": 0.15,
        "min_leg1_drop_pct": 3.0,
        "min_leg_balance": 0.20,
    },
    {   # Level 5: Loosest
        "name": "Very Loose",
        "min_mean_r2": 0.40,
        "min_weakest_r2": 0.25,
        "min_abs_slope_pct": 0.02,
        "max_nearness_pct": 15.0,
        "min_bounce_retrace": 0.10,
        "min_leg1_drop_pct": 2.0,
        "min_leg_balance": 0.15,
    },
]

MIN_RESULTS_TARGET = 10  # If fewer pass, relax to next level
