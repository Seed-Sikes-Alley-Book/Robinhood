#!/usr/bin/env python3
"""
Entry point for the W-pattern stock screener.

Usage:
    python main.py          # Launch GUI
    python main.py --cli    # Run in command-line mode
"""

import sys
import argparse
import os 

API_KEY="ROBINHOOD_API_KEY_TEST"
os.getenv(API_KEY,"/config.secrets.env")
API_KEY = os.getenv('ROBINHOOD_API_KEY_TEST')
BASE64_PRIVATE_KEY = os.getenv('BASE64_PRIVATE_KEY_TEST')

# Validate secrets
if not API_KEY:
    raise RuntimeError("Missing environment variable: ROBINHOOD_API_KEY_TEST")
if not BASE64_PRIVATE_KEY:
    raise RuntimeError("Missing environment variable: BASE64_PRIVATE_KEY_TEST")


def main():
    parser = argparse.ArgumentParser(
        description="W-Pattern Stock Screener (Forming Double Bottom)"
    )
    parser.add_argument(
        "--cli", action="store_true",
        help="Run in command-line mode without GUI"
    )
    parser.add_argument(
        "--tolerance", type=float, default=4.0,
        help="Residual tolerance %% (default: 4.0)"
    )
    parser.add_argument(
        "--refresh", action="store_true",
        help="Force refresh of market data"
    )
    
    args = parser.parse_args()
    
    if args.cli:
        from screener import run_screen, export_results, generate_all_charts
        
        print("=" * 60)
        print("W-Pattern Stock Screener (Forming Double Bottom)")
        print("=" * 60)
        
        results, level_used = run_screen(
            residual_tolerance=args.tolerance,
            force_refresh=args.refresh
        )
        
        if results:
            export_results(results, level_used)
            generate_all_charts(results)
            
            print("\n" + "=" * 60)
            print("TOP 10 MATCHES:")
            print("=" * 60)
            for i, r in enumerate(results[:10]):
                nearness = abs(r.current_price - r.first_low_price) / r.first_low_price * 100
                print(
                    f"{i+1:2}. {r.ticker:6} | Score: {r.shape_score:.3f} | "
                    f"Near Low: {nearness:.1f}% | R²: {r.mean_r2:.2f}"
                )
        else:
            print("No patterns found matching criteria.")
    else:
        from gui import run_gui
        run_gui()


if __name__ == "__main__":
    main()
