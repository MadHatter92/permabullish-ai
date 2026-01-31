"""
Stock Fundamentals Sync Script
Fetches and caches fundamental data for Nifty 500 stocks.
Run monthly to keep data fresh.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import json
import time
import re
import logging
import argparse
from typing import Optional, Dict, Any, List
from bs4 import BeautifulSoup
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Data source configuration
SOURCE_BASE = "https://www.screener.in"
SOURCE_PATH = "/company/{symbol}/consolidated/"
SOURCE_PATH_STANDALONE = "/company/{symbol}/"
REQUEST_DELAY = 0.5  # seconds between requests
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds


class FundamentalsFetcher:
    """Fetches fundamental stock data from public sources."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        })

    def fetch(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch fundamentals for a single stock."""
        # Try consolidated first, then standalone
        for path_template in [SOURCE_PATH, SOURCE_PATH_STANDALONE]:
            url = SOURCE_BASE + path_template.format(symbol=symbol)

            for attempt in range(MAX_RETRIES):
                try:
                    response = self.session.get(url, timeout=15)

                    if response.status_code == 200:
                        data = self._parse_page(response.text, symbol)
                        if data:
                            data['source_url'] = url
                            return data
                        break  # Page loaded but no data, try next path

                    elif response.status_code == 429:
                        # Rate limited - wait and retry
                        logger.warning(f"Rate limited, waiting {RETRY_DELAY}s...")
                        time.sleep(RETRY_DELAY)
                        continue

                    elif response.status_code == 404:
                        break  # Try next path

                    else:
                        logger.warning(f"Unexpected status {response.status_code} for {symbol}")
                        break

                except requests.exceptions.RequestException as e:
                    logger.error(f"Request failed for {symbol}: {e}")
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(RETRY_DELAY)
                    continue

        return None

    def _parse_page(self, html: str, symbol: str) -> Optional[Dict[str, Any]]:
        """Parse the HTML page and extract fundamental data."""
        soup = BeautifulSoup(html, 'html.parser')

        # Verify we got a valid company page
        if not soup.find('ul', id='top-ratios'):
            return None

        data = {'symbol': symbol.upper()}

        # Extract company name from h1 or title
        h1 = soup.find('h1', class_='margin-0')
        if h1:
            name_text = h1.get_text(strip=True)
            # Remove "consolidated" suffix if present
            data['company_name'] = name_text.replace('Consolidated', '').replace('Standalone', '').strip()
        else:
            # Fallback to title
            title = soup.find('title')
            if title:
                title_text = title.get_text()
                for separator in [' Stock Price', ' Share Price', ' - ']:
                    if separator in title_text:
                        data['company_name'] = title_text.split(separator)[0].strip()
                        break

        # Extract sector/industry from company info
        company_info = soup.find('div', class_='company-info')
        if company_info:
            info_text = company_info.get_text()
            # Try to extract sector
            sector_match = re.search(r'Sector:\s*([^\n]+)', info_text)
            if sector_match:
                data['sector'] = sector_match.group(1).strip()

        # Extract top ratios
        self._extract_ratios(soup, data)

        # Extract quarterly results
        data['quarterly_results'] = self._extract_table_data(soup, 'quarters')

        # Extract annual P&L
        data['profit_loss'] = self._extract_table_data(soup, 'profit-loss')

        # Extract balance sheet
        data['balance_sheet'] = self._extract_table_data(soup, 'balance-sheet')

        # Extract cash flow
        data['cash_flow'] = self._extract_table_data(soup, 'cash-flow')

        # Extract shareholding
        data['shareholding'] = self._extract_shareholding(soup)

        # Extract pros/cons
        data['pros'], data['cons'] = self._extract_pros_cons(soup)

        return data

    def _extract_ratios(self, soup: BeautifulSoup, data: Dict[str, Any]) -> None:
        """Extract key ratios from the top-ratios section."""
        ratios_ul = soup.find('ul', id='top-ratios')
        if not ratios_ul:
            return

        ratio_map = {
            'Market Cap': 'market_cap',
            'Current Price': 'current_price',
            'High / Low': 'high_low',
            'Stock P/E': 'pe_ratio',
            'Book Value': 'book_value',
            'Dividend Yield': 'dividend_yield',
            'ROCE': 'roce',
            'ROE': 'roe',
            'Face Value': 'face_value',
        }

        for li in ratios_ul.find_all('li', class_='flex'):
            name_span = li.find('span', class_='name')
            number_span = li.find('span', class_='number')

            if name_span and number_span:
                name = name_span.get_text(strip=True)
                value = number_span.get_text(strip=True)

                if name in ratio_map:
                    field = ratio_map[name]
                    if field == 'high_low':
                        data[field] = value
                    else:
                        data[field] = self._parse_number(value)

    def _extract_table_data(self, soup: BeautifulSoup, section_id: str) -> List[Dict]:
        """Extract data from a financial table section."""
        section = soup.find('section', id=section_id)
        if not section:
            return []

        table = section.find('table')
        if not table:
            return []

        results = []
        headers = []

        # Get headers (periods)
        header_row = table.find('thead')
        if header_row:
            for th in header_row.find_all('th'):
                headers.append(th.get_text(strip=True))

        # Get data rows
        tbody = table.find('tbody')
        if tbody:
            for tr in tbody.find_all('tr'):
                cells = tr.find_all(['th', 'td'])
                if len(cells) > 1:
                    row_name = cells[0].get_text(strip=True).rstrip('+')
                    row_data = {'metric': row_name}

                    for i, cell in enumerate(cells[1:], 1):
                        if i < len(headers):
                            period = headers[i]
                            value = self._parse_number(cell.get_text(strip=True))
                            row_data[period] = value

                    results.append(row_data)

        return results

    def _extract_shareholding(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract shareholding pattern data."""
        section = soup.find('section', id='shareholding')
        if not section:
            return []

        table = section.find('table')
        if not table:
            return []

        results = []
        headers = []

        # Get headers (quarters)
        header_row = table.find('thead')
        if header_row:
            for th in header_row.find_all('th'):
                headers.append(th.get_text(strip=True))

        # Get data rows
        tbody = table.find('tbody')
        if tbody:
            for tr in tbody.find_all('tr'):
                cells = tr.find_all(['th', 'td'])
                if len(cells) > 1:
                    holder_type = cells[0].get_text(strip=True).rstrip('+')
                    row_data = {'holder': holder_type}

                    for i, cell in enumerate(cells[1:], 1):
                        if i < len(headers):
                            period = headers[i]
                            value_text = cell.get_text(strip=True).replace('%', '')
                            row_data[period] = self._parse_number(value_text)

                    results.append(row_data)

        return results

    def _extract_pros_cons(self, soup: BeautifulSoup) -> tuple:
        """Extract pros and cons analysis."""
        pros = []
        cons = []

        pros_section = soup.find('div', class_='pros')
        if pros_section:
            for li in pros_section.find_all('li'):
                text = li.get_text(strip=True)
                if text:
                    pros.append(text)

        cons_section = soup.find('div', class_='cons')
        if cons_section:
            for li in cons_section.find_all('li'):
                text = li.get_text(strip=True)
                if text:
                    cons.append(text)

        return pros, cons

    def _parse_number(self, value: str) -> Optional[float]:
        """Parse a number from various formats."""
        if not value or value == '-':
            return None
        try:
            # Remove commas and percentage signs
            cleaned = value.replace(',', '').replace('%', '').strip()
            return float(cleaned)
        except ValueError:
            return None


def load_stock_list() -> List[Dict]:
    """Load stock list (prefers expanded NSE list, falls back to Nifty 500)."""
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')

    # Try expanded list first
    expanded_file = os.path.join(data_dir, 'nse_eq_stocks.json')
    if os.path.exists(expanded_file):
        with open(expanded_file, 'r') as f:
            return json.load(f)

    # Fall back to Nifty 500
    nifty_file = os.path.join(data_dir, 'nifty500_stocks.json')
    with open(nifty_file, 'r') as f:
        return json.load(f)


def get_db_connection():
    """Get database connection."""
    import psycopg2
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL environment variable not set")
    return psycopg2.connect(database_url)


def sync_all(symbols: List[str] = None, limit: int = None):
    """Sync fundamentals for all stocks or a subset."""
    from fundamentals_db import init_fundamentals_table, save_fundamentals, get_fundamentals_count

    # Load stock list if not provided
    if not symbols:
        stocks = load_stock_list()
        symbols = [s['symbol'] for s in stocks]

    if limit:
        symbols = symbols[:limit]

    logger.info(f"Starting sync for {len(symbols)} stocks...")

    # Initialize database
    conn = get_db_connection()
    init_fundamentals_table(conn)

    initial_count = get_fundamentals_count(conn)
    logger.info(f"Current fundamentals count: {initial_count}")

    fetcher = FundamentalsFetcher()
    success = 0
    failed = []

    for i, symbol in enumerate(symbols, 1):
        logger.info(f"[{i}/{len(symbols)}] Fetching {symbol}...")

        data = fetcher.fetch(symbol)

        if data:
            if save_fundamentals(conn, data):
                success += 1
                logger.info(f"  -> Saved: {data.get('company_name', symbol)}")
            else:
                failed.append(symbol)
                logger.error(f"  -> Failed to save")
        else:
            failed.append(symbol)
            logger.warning(f"  -> No data found")

        # Rate limiting
        time.sleep(REQUEST_DELAY)

    final_count = get_fundamentals_count(conn)
    conn.close()

    logger.info(f"\n{'='*50}")
    logger.info(f"Sync complete!")
    logger.info(f"  Success: {success}/{len(symbols)}")
    logger.info(f"  Failed: {len(failed)}")
    logger.info(f"  Total in DB: {final_count}")

    if failed:
        logger.info(f"  Failed symbols: {failed[:20]}{'...' if len(failed) > 20 else ''}")

    return success, failed


def sync_single(symbol: str) -> bool:
    """Sync fundamentals for a single stock."""
    from fundamentals_db import init_fundamentals_table, save_fundamentals

    conn = get_db_connection()
    init_fundamentals_table(conn)

    fetcher = FundamentalsFetcher()
    data = fetcher.fetch(symbol)

    if data:
        result = save_fundamentals(conn, data)
        conn.close()
        return result

    conn.close()
    return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sync stock fundamentals data")
    parser.add_argument('--symbol', '-s', help="Sync single symbol")
    parser.add_argument('--limit', '-l', type=int, help="Limit number of stocks")
    parser.add_argument('--test', '-t', action='store_true', help="Test mode - fetch but don't save")

    args = parser.parse_args()

    if args.test:
        # Test mode - just fetch and print
        fetcher = FundamentalsFetcher()
        symbol = args.symbol or 'RELIANCE'
        logger.info(f"Testing fetch for {symbol}...")
        data = fetcher.fetch(symbol)
        if data:
            print(json.dumps(data, indent=2, default=str))
        else:
            print("No data found")
    elif args.symbol:
        # Single symbol
        success = sync_single(args.symbol.upper())
        print(f"{'Success' if success else 'Failed'}")
    else:
        # Full sync
        sync_all(limit=args.limit)
