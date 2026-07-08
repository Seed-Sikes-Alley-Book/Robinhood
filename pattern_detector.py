"""
Core pattern detection: identifies forming double-bottom (W) patterns.
"""

import numpy as np
import pandas as pd
from scipy.signal import argrelextrema
from scipy.stats import linregress
from dataclasses import dataclass
from typing import Optional

from config import (
    TRAILING_WINDOWS, MIN_LEG_BARS, PIVOT_ORDER, WEIGHTS,
    DEFAULT_RESIDUAL_TOLERANCE, RELAXATION_LEVELS
)


@dataclass
class LegStats:
    """Statistics for a single leg of the pattern."""
    start_idx: int
    end_idx: int
    start_date: pd.Timestamp
    end_date: pd.Timestamp
    slope_pct_per_bar: float  # Slope as % change per bar
    r_squared: float
    residual_std_pct: float   # Residual std as % of mean price
    start_price: float
    end_price: float
    n_bars: int
    
    # Regression line parameters for plotting
    intercept: float
    slope_raw: float


@dataclass
class PatternResult:
    """Complete pattern detection result for one ticker."""
    ticker: str
    window_size: int
    shape_score: float
    legs: list[LegStats]
    
    # Component scores
    slope_conviction: float
    straightness: float
    leg_balance: float
    nearness_to_low: float
    bounce_amplitude: float
    drop_depth: float
    
    # Key levels
    first_low_price: float
    bounce_high_price: float
    current_price: float
    first_low_date: pd.Timestamp
    bounce_high_date: pd.Timestamp
    
    # Quality metrics
    mean_r2: float
    min_r2: float
    max_residual_pct: float
    
    # Full price series for plotting
    dates: pd.DatetimeIndex
    prices: np.ndarray


def find_local_extrema(
    prices: np.ndarray,
    order: int = 3
) -> tuple[np.ndarray, np.ndarray]:
    """
    Find local minima and maxima indices.
    
    Args:
        prices: Array of prices
        order: Number of points on each side to compare
        
    Returns:
        (minima_indices, maxima_indices)
    """
    minima = argrelextrema(prices, np.less_equal, order=order)[0]
    maxima = argrelextrema(prices, np.greater_equal, order=order)[0]
    return minima, maxima


def fit_leg(
    prices: np.ndarray,
    dates: pd.DatetimeIndex,
    start_idx: int,
    end_idx: int
) -> Optional[LegStats]:
    """
    Fit a linear regression to a price leg.
    
    Returns:
        LegStats if fit succeeds, None otherwise
    """
    if end_idx <= start_idx:
        return None
    
    n_bars = end_idx - start_idx + 1
    if n_bars < MIN_LEG_BARS:
        return None
    
    leg_prices = prices[start_idx:end_idx + 1]
    x = np.arange(len(leg_prices))
    
    try:
        result = linregress(x, leg_prices)
    except Exception:
        return None
    
    slope = result.slope
    intercept = result.intercept
    r_squared = result.rvalue ** 2
    
    # Predicted values and residuals
    predicted = intercept + slope * x
    residuals = leg_prices - predicted
    residual_std = np.std(residuals)
    
    # Express as percentages
    mean_price = np.mean(leg_prices)
    slope_pct = (slope / mean_price) * 100
    residual_std_pct = (residual_std / mean_price) * 100
    
    return LegStats(
        start_idx=start_idx,
        end_idx=end_idx,
        start_date=dates[start_idx],
        end_date=dates[end_idx],
        slope_pct_per_bar=slope_pct,
        r_squared=r_squared,
        residual_std_pct=residual_std_pct,
        start_price=prices[start_idx],
        end_price=prices[end_idx],
        n_bars=n_bars,
        intercept=intercept,
        slope_raw=slope
    )


def compute_shape_score(
    legs: list[LegStats],
    current_price: float,
    first_low: float,
    bounce_high: float,
    leg1_start: float
) -> dict[str, float]:
    """
    Compute the 0-1 shape score from weighted components.
    
    Returns:
        Dict with component scores and final shape_score
    """
    # 1. Slope conviction: how strongly directional are the slopes
    slopes = [abs(leg.slope_pct_per_bar) for leg in legs]
    # Normalize slopes (typical strong slope ~0.3-0.5%/bar)
    slope_scores = [min(s / 0.4, 1.0) for s in slopes]
    slope_conviction = np.mean(slope_scores)
    
    # 2. Straightness: average R²
    straightness = np.mean([leg.r_squared for leg in legs])
    
    # 3. Leg balance: how symmetric are leg lengths
    lengths = [leg.n_bars for leg in legs]
    min_len, max_len = min(lengths), max(lengths)
    leg_balance = min_len / max_len if max_len > 0 else 0
    
    # 4. Nearness to first low: current price close to first low
    price_range = bounce_high - first_low
    if price_range > 0:
        distance_from_low = abs(current_price - first_low)
        nearness_ratio = distance_from_low / price_range
        nearness_to_low = max(0, 1 - nearness_ratio)
    else:
        nearness_to_low = 0
    
    # 5. Bounce amplitude: how much did the bounce retrace leg 1
    leg1_drop = leg1_start - first_low
    bounce = bounce_high - first_low
    if leg1_drop > 0:
        bounce_amplitude = min(bounce / leg1_drop, 1.0)
    else:
        bounce_amplitude = 0
    
    # 6. Drop depth: how significant was the initial decline
    if leg1_start > 0:
        drop_pct = (leg1_drop / leg1_start) * 100
        # Normalize (10% drop = score 1.0)
        drop_depth = min(drop_pct / 10, 1.0)
    else:
        drop_depth = 0
    
    # Weighted combination
    shape_score = (
        WEIGHTS["slope_conviction"] * slope_conviction +
        WEIGHTS["straightness"] * straightness +
        WEIGHTS["leg_balance"] * leg_balance +
        WEIGHTS["nearness_to_low"] * nearness_to_low +
        WEIGHTS["bounce_amplitude"] * bounce_amplitude +
        WEIGHTS["drop_depth"] * drop_depth
    )
    
    return {
        "shape_score": shape_score,
        "slope_conviction": slope_conviction,
        "straightness": straightness,
        "leg_balance": leg_balance,
        "nearness_to_low": nearness_to_low,
        "bounce_amplitude": bounce_amplitude,
        "drop_depth": drop_depth
    }


def detect_pattern_in_window(
    prices: np.ndarray,
    dates: pd.DatetimeIndex,
    residual_tolerance: float = DEFAULT_RESIDUAL_TOLERANCE
) -> Optional[PatternResult]:
    """
    Attempt to detect a W pattern in a price window.
    
    Searches for the best pivot combination that yields:
    - 3 legs with down/up/down slopes
    - Acceptable fit quality
    """
    n = len(prices)
    if n < 3 * MIN_LEG_BARS:
        return None
    
    # Find candidate pivots
    minima, maxima = find_local_extrema(prices, order=PIVOT_ORDER)
    
    # Filter extrema to reasonable positions
    # First bottom should be in first 60% of window
    # Bounce peak should be after first bottom, before last 20%
    valid_minima = minima[(minima >= MIN_LEG_BARS) & (minima < int(n * 0.6))]
    valid_maxima = maxima[(maxima >= 2 * MIN_LEG_BARS) & (maxima < int(n * 0.85))]
    
    if len(valid_minima) == 0 or len(valid_maxima) == 0:
        return None
    
    best_result = None
    best_score = -1
    
    # Try combinations of first_bottom and bounce_peak
    for first_bottom_idx in valid_minima:
        for bounce_peak_idx in valid_maxima:
            # Bounce must be after first bottom with enough room
            if bounce_peak_idx <= first_bottom_idx + MIN_LEG_BARS:
                continue
            # Need room for leg 3
            if n - 1 - bounce_peak_idx < MIN_LEG_BARS:
                continue
            
            # Fit three legs: [0 → first_bottom], [first_bottom → bounce], [bounce → end]
            leg1 = fit_leg(prices, dates, 0, first_bottom_idx)
            leg2 = fit_leg(prices, dates, first_bottom_idx, bounce_peak_idx)
            leg3 = fit_leg(prices, dates, bounce_peak_idx, n - 1)
            
            if not all([leg1, leg2, leg3]):
                continue
            
            legs = [leg1, leg2, leg3]
            
            # HARD REQUIREMENT: down/up/down slopes
            if not (leg1.slope_pct_per_bar < 0 and 
                    leg2.slope_pct_per_bar > 0 and 
                    leg3.slope_pct_per_bar < 0):
                continue
            
            # Quality gate: residual tolerance
            max_residual = max(leg.residual_std_pct for leg in legs)
            if max_residual > residual_tolerance:
                continue
            
            # Compute shape score
            first_low = prices[first_bottom_idx]
            bounce_high = prices[bounce_peak_idx]
            current_price = prices[-1]
            leg1_start = prices[0]
            
            scores = compute_shape_score(
                legs, current_price, first_low, bounce_high, leg1_start
            )
            
            if scores["shape_score"] > best_score:
                best_score = scores["shape_score"]
                best_result = PatternResult(
                    ticker="",  # Filled by caller
                    window_size=n,
                    shape_score=scores["shape_score"],
                    legs=legs,
                    slope_conviction=scores["slope_conviction"],
                    straightness=scores["straightness"],
                    leg_balance=scores["leg_balance"],
                    nearness_to_low=scores["nearness_to_low"],
                    bounce_amplitude=scores["bounce_amplitude"],
                    drop_depth=scores["drop_depth"],
                    first_low_price=first_low,
                    bounce_high_price=bounce_high,
                    current_price=current_price,
                    first_low_date=dates[first_bottom_idx],
                    bounce_high_date=dates[bounce_peak_idx],
                    mean_r2=np.mean([leg.r_squared for leg in legs]),
                    min_r2=min(leg.r_squared for leg in legs),
                    max_residual_pct=max_residual,
                    dates=dates,
                    prices=prices
                )
    
    return best_result


def detect_pattern(
    ticker: str,
    df: pd.DataFrame,
    residual_tolerance: float = DEFAULT_RESIDUAL_TOLERANCE
) -> Optional[PatternResult]:
    """
    Detect best W pattern for a ticker across multiple trailing windows.
    """
    prices_full = df["Close"].values
    dates_full = df.index
    n = len(prices_full)
    
    best_result = None
    best_score = -1
    
    for window in TRAILING_WINDOWS:
        if window > n:
            continue
        
        # Take trailing window
        prices = prices_full[-window:]
        dates = dates_full[-window:]
        
        result = detect_pattern_in_window(prices, dates, residual_tolerance)
        
        if result and result.shape_score > best_score:
            best_score = result.shape_score
            best_result = result
            best_result.ticker = ticker
    
    return best_result


def passes_relaxation_level(
    result: PatternResult,
    level: dict
) -> bool:
    """
    Check if a pattern result passes the gates for a relaxation level.
    """
    # Mean R²
    if result.mean_r2 < level["min_mean_r2"]:
        return False
    
    # Weakest leg R²
    if result.min_r2 < level["min_weakest_r2"]:
        return False
    
    # Minimum slope magnitude per leg
    for leg in result.legs:
        if abs(leg.slope_pct_per_bar) < level["min_abs_slope_pct"]:
            return False
    
    # Nearness to first low
    price_diff_pct = abs(result.current_price - result.first_low_price) / result.first_low_price * 100
    if price_diff_pct > level["max_nearness_pct"]:
        return False
    
    # Bounce retrace
    leg1_drop = result.legs[0].start_price - result.first_low_price
    bounce = result.bounce_high_price - result.first_low_price
    if leg1_drop > 0:
        retrace = bounce / leg1_drop
        if retrace < level["min_bounce_retrace"]:
            return False
    
    # Leg 1 drop %
    if result.legs[0].start_price > 0:
        drop_pct = leg1_drop / result.legs[0].start_price * 100
        if drop_pct < level["min_leg1_drop_pct"]:
            return False
    
    # Leg length balance
    lengths = [leg.n_bars for leg in result.legs]
    balance = min(lengths) / max(lengths) if max(lengths) > 0 else 0
    if balance < level["min_leg_balance"]:
        return False
    
    return True


def filter_by_relaxation(
    results: list[PatternResult],
    min_target: int = 10
) -> tuple[list[PatternResult], dict]:
    """
    Filter results using relaxation levels, starting strict and loosening if needed.
    
    Returns:
        (filtered_results, level_used)
    """
    for level in RELAXATION_LEVELS:
        passing = [r for r in results if passes_relaxation_level(r, level)]
        if len(passing) >= min_target:
            return passing, level
    
    # Return whatever we have with loosest level
    return (
        [r for r in results if passes_relaxation_level(r, RELAXATION_LEVELS[-1])],
        RELAXATION_LEVELS[-1]
    )
