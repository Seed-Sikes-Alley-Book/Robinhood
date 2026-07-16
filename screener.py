"""
Main screener orchestration: runs the scan and generates outputs.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt 
import matplotlib.dates as mdates 
from pathlib import Path
from typing import Optional

from config import (
    DATA_DIR, RESULTS_FILE, CHARTS_DIR,
    DEFAULT_RESIDUAL_TOLERANCE, MIN_RESULTS_TARGET
)
from data_loader import load_universe
from pattern_detector import (
    detect_pattern, filter_by_relaxation, PatternResult
)


def run_screen(
    residual_tolerance: float = DEFAULT_RESIDUAL_TOLERANCE,
    force_refresh: bool = False,
    progress_callback: Optional[callable] = None
) -> tuple[list[PatternResult], dict]:
    """
    Run the full screening process.
    
    Args:
        residual_tolerance: Max residual std % for quality gate
        force_refresh: Force re-download of data
        progress_callback: Optional callback(current, total, ticker) for progress
        
    Returns:
        (sorted_results, relaxation_level_used)
    """
    # Load data
    universe = load_universe(force_refresh)
    
    # Detect patterns
    all_results = []
    total = len(universe)
    
    for i, (ticker, df) in enumerate(universe.items()):
        if progress_callback:
            progress_callback(i + 1, total, ticker)
        
        result = detect_pattern(ticker, df, residual_tolerance)
        if result:
            all_results.append(result)
    
    print(f"\nFound {len(all_results)} raw pattern matches")
    
    # Apply relaxation filtering
    filtered, level_used = filter_by_relaxation(all_results, MIN_RESULTS_TARGET)
    
    # Sort by shape_score descending
    filtered.sort(key=lambda x: x.shape_score, reverse=True)
    
    print(f"Filtered to {len(filtered)} matches using '{level_used['name']}' level")
    
    return filtered, level_used


def export_results(results: list[PatternResult], level_used: dict) -> Path:
    """Export screening results to CSV."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    rows = []
    for r in results:
        rows.append({
            "ticker": r.ticker,
            "shape_score": round(r.shape_score, 4),
            "window_size": r.window_size,
            "current_price": round(r.current_price, 2),
            "first_low": round(r.first_low_price, 2),
            "first_low_date": r.first_low_date.strftime("%Y-%m-%d"),
            "bounce_high": round(r.bounce_high_price, 2),
            "bounce_high_date": r.bounce_high_date.strftime("%Y-%m-%d"),
            "nearness_pct": round(
                abs(r.current_price - r.first_low_price) / r.first_low_price * 100, 2
            ),
            "mean_r2": round(r.mean_r2, 3),
            "min_r2": round(r.min_r2, 3),
            "max_residual_pct": round(r.max_residual_pct, 2),
            "leg1_slope": round(r.legs[0].slope_pct_per_bar, 3),
            "leg2_slope": round(r.legs[1].slope_pct_per_bar, 3),
            "leg3_slope": round(r.legs[2].slope_pct_per_bar, 3),
            "leg1_bars": r.legs[0].n_bars,
            "leg2_bars": r.legs[1].n_bars,
            "leg3_bars": r.legs[2].n_bars,
            "relaxation_level": level_used["name"],
        })
    
    df = pd.DataFrame(rows)
    df.to_csv(RESULTS_FILE, index=False)
    print(f"Results exported to {RESULTS_FILE}")
    
    return RESULTS_FILE


def plot_pattern(result: PatternResult, save_path: Optional[Path] = None) -> plt.Figure:
    """
    Plot a detected pattern with regression lines and confidence bands.
    """
    fig, ax = plt.subplots(figsize=(12, 6))
    
    dates = result.dates
    prices = result.prices
    
    # Plot price series
    ax.plot(dates, prices, "b-", linewidth=1.5, label="Price", alpha=0.8)
    
    # Colors for legs
    leg_colors = ["#d62728", "#2ca02c", "#d62728"]  # red, green, red
    leg_labels = ["Leg 1 (down)", "Leg 2 (up)", "Leg 3 (down)"]
    
    for i, leg in enumerate(result.legs):
        # Generate regression line
        leg_dates = dates[leg.start_idx:leg.end_idx + 1]
        x = np.arange(leg.n_bars)
        y_fit = leg.intercept + leg.slope_raw * x
        
        # Compute 2σ bands
        leg_prices = prices[leg.start_idx:leg.end_idx + 1]
        residuals = leg_prices - y_fit
        sigma = np.std(residuals)
        
        # Plot regression line
        ax.plot(
            leg_dates, y_fit,
            color=leg_colors[i], linewidth=2, linestyle="--",
            label=f"{leg_labels[i]} (R²={leg.r_squared:.2f})"
        )
        
        # Plot ±2σ band
        ax.fill_between(
            leg_dates,
            y_fit - 2 * sigma,
            y_fit + 2 * sigma,
            color=leg_colors[i],
            alpha=0.15
        )
    
    # Mark pivots
    first_bottom_idx = result.legs[0].end_idx
    bounce_peak_idx = result.legs[1].end_idx
    
    ax.scatter(
        [dates[first_bottom_idx]], [prices[first_bottom_idx]],
        color="purple", s=100, zorder=5, marker="v",
        label=f"First Low ({result.first_low_date.strftime('%Y-%m-%d')})"
    )
    ax.scatter(
        [dates[bounce_peak_idx]], [prices[bounce_peak_idx]],
        color="orange", s=100, zorder=5, marker="^",
        label=f"Bounce High ({result.bounce_high_date.strftime('%Y-%m-%d')})"
    )
    
    # Formatting
    ax.set_title(
        f"{result.ticker} - Forming Double Bottom (W)\n"
        f"Shape Score: {result.shape_score:.3f} | Window: {result.window_size} bars",
        fontsize=12, fontweight="bold"
    )
    ax.set_xlabel("Date")
    ax.set_ylabel("Price ($)")
    ax.legend(loc="upper left", fontsize=8)
    ax.grid(True, alpha=0.3)
    
    # Date formatting
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
    fig.autofmt_xdate()
    
    plt.tight_layout()
    
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    
    return fig


def generate_all_charts(results: list[PatternResult], max_charts: int = 20) -> Path:
    """Generate charts for top results."""
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Clear old charts
    for f in CHARTS_DIR.glob("*.png"):
        f.unlink()
    
    for i, result in enumerate(results[:max_charts]):
        save_path = CHARTS_DIR / f"{i+1:02d}_{result.ticker}.png"
        fig = plot_pattern(result, save_path)
        plt.close(fig)
    
    print(f"Generated {min(len(results), max_charts)} charts in {CHARTS_DIR}")
    return CHARTS_DIR
