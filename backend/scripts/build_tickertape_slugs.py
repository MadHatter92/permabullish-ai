"""
Script to build Tickertape slug mappings for all Nifty 500 stocks.
Uses Tickertape's search API to get official slugs.
"""

import requests
import json
import time
from typing import Optional, Dict, List

def get_nifty500_symbols() -> List[str]:
    """Fetch all Nifty 500 symbols from NSE."""
    url = "https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%20500"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
    }

    session = requests.Session()
    # Get cookies first
    session.get("https://www.nseindia.com", headers=headers, timeout=10)

    response = session.get(url, headers=headers, timeout=15)
    data = response.json()

    symbols = []
    for item in data.get("data", []):
        symbol = item.get("symbol", "")
        if symbol and symbol != "NIFTY 500":
            symbols.append(symbol)

    return symbols


def get_tickertape_slug(symbol: str, session: requests.Session) -> Optional[str]:
    """Get Tickertape slug using their search API."""
    search_url = f"https://api.tickertape.in/search?text={symbol}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
    }

    try:
        response = session.get(search_url, headers=headers, timeout=10)
        data = response.json()

        if data.get("success") and data.get("data", {}).get("stocks"):
            stocks = data["data"]["stocks"]
            # Find exact match by ticker
            for stock in stocks:
                if stock.get("ticker", "").upper() == symbol.upper():
                    slug = stock.get("slug", "")
                    if slug.startswith("/stocks/"):
                        return slug[8:]  # Remove '/stocks/' prefix
                    return slug

            # If no exact match, use first result if it's close
            if stocks and stocks[0].get("match") == "EXACT":
                slug = stocks[0].get("slug", "")
                if slug.startswith("/stocks/"):
                    return slug[8:]
                return slug

        return None
    except Exception as e:
        print(f"Error fetching slug for {symbol}: {e}")
        return None


def build_slug_mapping():
    """Build the complete mapping of symbols to Tickertape slugs."""
    print("Fetching Nifty 500 symbols from NSE...")
    symbols = get_nifty500_symbols()
    print(f"Found {len(symbols)} symbols\n")

    session = requests.Session()
    mapping = {}
    failed = []

    for i, symbol in enumerate(symbols):
        print(f"[{i+1}/{len(symbols)}] {symbol}...", end=" ", flush=True)

        slug = get_tickertape_slug(symbol, session)

        if slug:
            mapping[symbol] = slug
            print(f"-> {slug}")
        else:
            failed.append(symbol)
            print("FAILED")

        # Rate limiting - be nice to Tickertape
        time.sleep(0.2)  # 5 requests per second max

    print(f"\n\nCompleted: {len(mapping)} successful, {len(failed)} failed")

    if failed:
        print(f"\nFailed symbols ({len(failed)}): {failed[:20]}{'...' if len(failed) > 20 else ''}")

    # Save to JSON file
    output_file = "tickertape_slugs.json"
    with open(output_file, "w") as f:
        json.dump(mapping, f, indent=2, sort_keys=True)
    print(f"\nSaved to {output_file}")

    # Output Python dict format
    print("\n\n# ========== COPY BELOW TO stock_providers.py ==========")
    print("SYMBOL_SLUGS = {")
    for symbol in sorted(mapping.keys()):
        print(f'    "{symbol}": "{mapping[symbol]}",')
    print("}")
    print("# ========== END COPY ==========")

    return mapping, failed


if __name__ == "__main__":
    mapping, failed = build_slug_mapping()
