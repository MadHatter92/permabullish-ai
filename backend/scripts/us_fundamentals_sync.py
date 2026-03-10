"""
US Stock Fundamentals Sync Script
Fetches and caches fundamental data for S&P 500 stocks from Financial Modeling Prep (FMP).
Similar to the Screener.in sync for Indian stocks.

Usage:
    python scripts/us_fundamentals_sync.py [--limit N] [--symbol AAPL]

Run weekly via cron to keep US stock data warm.
FMP free tier: 250 calls/day. S&P 500 = ~500 stocks x 5 endpoints = 2500 calls.
With 45-day cache, only stale stocks need refresh (~70/week), fitting in daily limit.
"""

import sys
import os
import json
import time
import argparse
import logging
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data_sources.fmp import fetch_us_fundamentals, get_api_usage

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Staleness threshold (days)
STALE_DAYS = 45


def load_sp500_symbols() -> list:
    """Load S&P 500 stock symbols from JSON file."""
    data_dir = Path(__file__).parent.parent / "data"
    sp500_file = data_dir / "sp500_stocks.json"

    if not sp500_file.exists():
        logger.error(f"S&P 500 stock list not found at {sp500_file}")
        return []

    with open(sp500_file, 'r') as f:
        stocks = json.load(f)

    return [s["symbol"] for s in stocks]


def get_cached_symbols_with_dates(conn) -> dict:
    """Get symbols and their last_updated dates from the fundamentals table."""
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT symbol, last_updated FROM stock_fundamentals")
        return {row[0]: row[1] for row in cursor.fetchall()}
    except Exception:
        return {}


def save_fundamentals_to_db(conn, data: dict) -> bool:
    """Save US stock fundamentals to the database."""
    try:
        from fundamentals_db import save_fundamentals
        return save_fundamentals(conn, data)
    except Exception as e:
        logger.error(f"Failed to save fundamentals for {data.get('symbol')}: {e}")
        return False


def sync_us_fundamentals(limit: int = 50, symbol: str = None):
    """
    Sync US stock fundamentals from FMP.

    Args:
        limit: Max number of stocks to sync in this run
        symbol: If specified, sync only this symbol
    """
    import database as db

    # Get database connection
    conn = db.get_connection()

    if symbol:
        symbols = [symbol.upper()]
        logger.info(f"Syncing single symbol: {symbol}")
    else:
        symbols = load_sp500_symbols()
        if not symbols:
            logger.error("No symbols to sync")
            return

        # Check which symbols need refresh
        cached = get_cached_symbols_with_dates(conn)
        cutoff = datetime.now() - timedelta(days=STALE_DAYS)

        stale_symbols = []
        for sym in symbols:
            last_updated = cached.get(sym)
            if last_updated is None:
                stale_symbols.append(sym)
            elif isinstance(last_updated, str):
                try:
                    updated_dt = datetime.fromisoformat(last_updated.replace('Z', '+00:00').split('+')[0])
                    if updated_dt < cutoff:
                        stale_symbols.append(sym)
                except (ValueError, TypeError):
                    stale_symbols.append(sym)

        logger.info(f"S&P 500: {len(symbols)} total, {len(cached)} cached, {len(stale_symbols)} stale/missing")
        symbols = stale_symbols[:limit]

    if not symbols:
        logger.info("All symbols are fresh, nothing to sync")
        return

    # Check FMP API availability
    usage = get_api_usage()
    if not usage["has_api_key"]:
        logger.error("FMP_API_KEY not set. Set it in environment variables.")
        return

    logger.info(f"FMP API usage: {usage['calls_today']}/{usage['daily_limit']} calls today")
    logger.info(f"Syncing {len(symbols)} symbols...")

    success_count = 0
    fail_count = 0

    for i, sym in enumerate(symbols):
        # Check API budget
        current_usage = get_api_usage()
        if current_usage["remaining"] < 10:
            logger.warning(f"Low API budget ({current_usage['remaining']} remaining), stopping sync")
            break

        logger.info(f"[{i+1}/{len(symbols)}] Fetching {sym}...")

        try:
            data = fetch_us_fundamentals(sym)
            if data:
                if save_fundamentals_to_db(conn, data):
                    success_count += 1
                    logger.info(f"  Saved {sym} fundamentals")
                else:
                    fail_count += 1
                    logger.warning(f"  Failed to save {sym}")
            else:
                fail_count += 1
                logger.warning(f"  No data returned for {sym}")

            # Rate limit: ~1 request/second to be safe
            time.sleep(1.2)

        except Exception as e:
            fail_count += 1
            logger.error(f"  Error syncing {sym}: {e}")

    conn.close()

    final_usage = get_api_usage()
    logger.info(f"\nSync complete: {success_count} success, {fail_count} failed")
    logger.info(f"FMP API calls used this session: {final_usage['calls_today'] - usage['calls_today']}")
    logger.info(f"Total API calls today: {final_usage['calls_today']}/{final_usage['daily_limit']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sync US stock fundamentals from FMP")
    parser.add_argument("--limit", type=int, default=50, help="Max stocks to sync (default: 50)")
    parser.add_argument("--symbol", type=str, help="Sync a specific symbol only")
    args = parser.parse_args()

    sync_us_fundamentals(limit=args.limit, symbol=args.symbol)
