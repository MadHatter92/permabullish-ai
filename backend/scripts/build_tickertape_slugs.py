"""
Script to build Tickertape slug mappings for all Nifty 500 stocks.
Uses Tickertape's search API to get official slugs.
Falls back to company name search when ticker search fails.
"""

import requests
import json
import time
import os
from typing import Optional, Dict, List, Tuple


def load_nifty500_from_json() -> Dict[str, str]:
    """Load symbol to company name mapping from local JSON file."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(script_dir, "..", "data", "nifty500_stocks.json")

    if not os.path.exists(json_path):
        return {}

    with open(json_path, "r", encoding="utf-8") as f:
        stocks = json.load(f)

    return {stock["symbol"]: stock.get("company_name", "") for stock in stocks}


def get_nifty500_symbols() -> Tuple[List[str], Dict[str, str]]:
    """Fetch all Nifty 500 symbols from NSE and load company names from local JSON."""
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
    nse_names = {}  # symbol -> company name from NSE
    for item in data.get("data", []):
        symbol = item.get("symbol", "")
        if symbol and symbol != "NIFTY 500":
            symbols.append(symbol)
            # NSE provides company name too
            nse_names[symbol] = item.get("meta", {}).get("companyName", "") or item.get("identifier", "")

    # Load names from local JSON (more complete)
    local_names = load_nifty500_from_json()

    # Merge: prefer local names, fall back to NSE names
    company_names = {}
    for symbol in symbols:
        company_names[symbol] = local_names.get(symbol) or nse_names.get(symbol, "")

    return symbols, company_names


def search_tickertape(query: str, symbol: str, session: requests.Session) -> Optional[str]:
    """Search Tickertape and return slug if found for the given symbol."""
    search_url = f"https://api.tickertape.in/search?text={requests.utils.quote(query)}"
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

            # If no exact ticker match but searching by name, use first stock result
            # that matches the symbol in its slug (e.g., "varun-beverages-VBL" contains "VBL")
            for stock in stocks:
                slug = stock.get("slug", "")
                if slug.startswith("/stocks/"):
                    slug = slug[8:]
                # Check if symbol appears in slug (case insensitive)
                if symbol.upper() in slug.upper():
                    return slug

        return None
    except Exception as e:
        print(f"Error searching '{query}': {e}")
        return None


def get_tickertape_slug(symbol: str, company_name: str, session: requests.Session) -> Tuple[Optional[str], str]:
    """
    Get Tickertape slug using their search API.
    First tries by ticker symbol, then falls back to company name.
    Returns (slug, method) where method is 'ticker' or 'name' or 'failed'.
    """
    # First, try searching by ticker symbol
    slug = search_tickertape(symbol, symbol, session)
    if slug:
        return slug, "ticker"

    # If ticker search fails and we have a company name, try that
    if company_name:
        # Clean up company name - remove "Limited", "Ltd", etc. for better search
        clean_name = company_name
        for suffix in [" Limited", " Ltd.", " Ltd", " India", " (India)"]:
            clean_name = clean_name.replace(suffix, "")
        clean_name = clean_name.strip()

        if clean_name:
            time.sleep(0.15)  # Small delay between searches
            slug = search_tickertape(clean_name, symbol, session)
            if slug:
                return slug, "name"

    return None, "failed"


def build_slug_mapping():
    """Build the complete mapping of symbols to Tickertape slugs."""
    print("Fetching Nifty 500 symbols from NSE...")
    symbols, company_names = get_nifty500_symbols()
    print(f"Found {len(symbols)} symbols")
    print(f"Loaded company names for {sum(1 for n in company_names.values() if n)} stocks\n")

    session = requests.Session()
    mapping = {}
    failed = []
    found_by_ticker = 0
    found_by_name = 0

    for i, symbol in enumerate(symbols):
        name = company_names.get(symbol, "")
        name_display = f" ({name[:30]}...)" if len(name) > 30 else f" ({name})" if name else ""
        print(f"[{i+1}/{len(symbols)}] {symbol}{name_display}...", end=" ", flush=True)

        slug, method = get_tickertape_slug(symbol, name, session)

        if slug:
            mapping[symbol] = slug
            if method == "ticker":
                found_by_ticker += 1
                print(f"-> {slug}")
            else:
                found_by_name += 1
                print(f"-> {slug} (via name)")
        else:
            failed.append(symbol)
            print("FAILED")

        # Rate limiting - be nice to Tickertape
        time.sleep(0.2)  # 5 requests per second max

    print(f"\n\nCompleted: {len(mapping)} successful ({found_by_ticker} by ticker, {found_by_name} by name), {len(failed)} failed")

    if failed:
        print(f"\nFailed symbols ({len(failed)}): {failed[:20]}{'...' if len(failed) > 20 else ''}")

    # Save to JSON file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_file = os.path.join(script_dir, "..", "data", "tickertape_slugs.json")
    with open(output_file, "w", encoding="utf-8") as f:
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
