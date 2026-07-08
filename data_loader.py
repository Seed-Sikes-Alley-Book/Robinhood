"""
Data loading module: fetches OHLCV from Yahoo Finance with local caching.
"""

import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import warnings

from config import (
    DATA_DIR, CACHE_FILE, LOOKBACK_YEARS,
    MIN_MARKET_CAP, MIN_AVG_VOLUME_60D
)

warnings.filterwarnings("ignore", category=FutureWarning)


def get_sp500_tickers() -> list[str]:
    """Fetch S&P 500 tickers from Wikipedia."""
    try:
        tables = pd.read_html(
            "[en.wikipedia.org](https://en.wikipedia.org/wiki/List_of_S%26P_500_companies)"
        )
        df = tables[0]
        tickers = df["Symbol"].str.replace(".", "-", regex=False).tolist()
        return tickers
    except Exception as e:
        print(f"Failed to fetch S&P 500 list: {e}")
        # Fallback to a subset
        return [
            "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA",
            "JPM", "V", "JNJ", "WMT", "PG", "UNH", "HD", "MA", "BAC",
            "XOM", "PFE", "COST", "CVX", "ABBV", "KO", "MRK", "PEP",
            "TMO", "AVGO", "CSCO", "ACN", "MCD", "ABT", "DHR", "NKE"
        ]


def get_additional_tickers() -> list[str]:
    """Add commonly traded mid/large caps outside S&P 500."""
    return [
        "PLTR", "RIVN", "LCID", "SOFI", "HOOD", "COIN", "SNOW", "NET",
        "DKNG", "RBLX", "U", "PATH", "ZS", "CRWD", "OKTA", "TWLO"
    ]


def filter_by_fundamentals(tickers: list[str]) -> list[str]:
    """Filter tickers by market cap and volume requirements."""
    valid = []
    print(f"Filtering {len(tickers)} tickers by fundamentals...")
    
    for i, ticker in enumerate(tickers):
        if (i + 1) % 50 == 0:
            print(f"  Checked {i + 1}/{len(tickers)}...")
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            market_cap = info.get("marketCap", 0) or 0
            avg_volume = info.get("averageVolume", 0) or 0
            
            if market_cap >= MIN_MARKET_CAP and avg_volume >= MIN_AVG_VOLUME_60D:
                valid.append(ticker)
        except Exception:
            continue
    
    print(f"  {len(valid)} tickers passed fundamental filters")
    return valid


def fetch_ohlcv(
    tickers: list[str],
    force_refresh: bool = False
) -> dict[str, pd.DataFrame]:
    """
    Fetch OHLCV data for tickers, using cache when available.
    
    Returns:
        Dict mapping ticker -> DataFrame with columns [Open, High, Low, Close, Volume]
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # Check cache
    if CACHE_FILE.exists() and not force_refresh:
        cache_age = datetime.now() - datetime.fromtimestamp(
            CACHE_FILE.stat().st_mtime
        )
        if cache_age < timedelta(hours=18):
            print("Loading data from cache...")
            return _load_cache()
    
    print("Fetching fresh data from Yahoo Finance...")
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=LOOKBACK_YEARS * 365)
    
    data = {}
    failed = []
    
    for i, ticker in enumerate(tickers):
        if (i + 1) % 25 == 0:
            print(f"  Downloaded {i + 1}/{len(tickers)}...")
        try:
            df = yf.download(
                ticker,
                start=start_date,
                end=end_date,
                progress=False,
                auto_adjust=True
            )
            if len(df) >= 100:  # Need enough history
                # Handle multi-level columns from yfinance
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                data[ticker] = df[["Open", "High", "Low", "Close", "Volume"]]
        except Exception:
            failed.append(ticker)
    
    if failed:
        print(f"  Failed to download: {len(failed)} tickers")
    
    # Save to cache
    _save_cache(data)
    print(f"Cached {len(data)} tickers to {CACHE_FILE}")
    
    return data


def _save_cache(data: dict[str, pd.DataFrame]) -> None:
    """Save data dict to parquet files."""
    combined = []
    for ticker, df in data.items():
        df = df.copy()
        df["ticker"] = ticker
        combined.append(df)
    
    if combined:
        full_df = pd.concat(combined)
        full_df.to_parquet(CACHE_FILE)


def _load_cache() -> dict[str, pd.DataFrame]:
    """Load data from parquet cache."""
    full_df = pd.read_parquet(CACHE_FILE)
    data = {}
    for ticker in full_df["ticker"].unique():
        df = full_df[full_df["ticker"] == ticker].drop(columns=["ticker"])
        data[ticker] = df.sort_index()
    return data


def load_universe(force_refresh: bool = False) -> dict[str, pd.DataFrame]:
    """
    Main entry: load filtered universe with OHLCV data.
    """
    # Get tickers
    tickers = get_sp500_tickers() + get_additional_tickers()
    tickers = list(set(tickers))  # Dedupe
    
    # Filter by fundamentals (cached check built into fetch)
    if force_refresh or not CACHE_FILE.exists():
        tickers = filter_by_fundamentals(tickers)
    
    # Fetch OHLCV
    data = fetch_ohlcv(tickers, force_refresh)
    
    # Secondary volume filter on actual data
    filtered = {}
    for ticker, df in data.items():
        if len(df) >= 130:  # Need enough for largest window
            avg_vol_60 = df["Volume"].tail(60).mean()
            if avg_vol_60 >= MIN_AVG_VOLUME_60D:
                filtered[ticker] = df
    
    print(f"Universe: {len(filtered)} stocks after all filters")
    return filtered
