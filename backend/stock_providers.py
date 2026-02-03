"""
Multi-source stock data providers with automatic rotation and fallback.
Providers: Yahoo Finance (primary), Tickertape (backup), Alpha Vantage (fallback)
"""

import requests
import yfinance as yf
import re
import json
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import logging

from config import NSE_SUFFIX, BSE_SUFFIX
from pathlib import Path

logger = logging.getLogger(__name__)

# Load Tickertape slugs from JSON file
def _load_tickertape_slugs() -> dict:
    """Load Tickertape symbol-to-slug mapping from JSON file."""
    slugs_file = Path(__file__).parent / "data" / "tickertape_slugs.json"
    try:
        if slugs_file.exists():
            with open(slugs_file, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load Tickertape slugs: {e}")
    return {}

TICKERTAPE_SLUGS = _load_tickertape_slugs()

# Simple in-memory cache with TTL
class SimpleCache:
    def __init__(self, default_ttl: int = 3600):
        self._cache: Dict[str, tuple] = {}  # key -> (value, expiry_time)
        self.default_ttl = default_ttl

    def get(self, key: str) -> Optional[Any]:
        if key in self._cache:
            value, expiry = self._cache[key]
            if datetime.now().timestamp() < expiry:
                return value
            else:
                del self._cache[key]
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        expiry = datetime.now().timestamp() + (ttl or self.default_ttl)
        self._cache[key] = (value, expiry)

    def clear(self):
        self._cache.clear()


# Global cache instance (1 hour TTL)
stock_cache = SimpleCache(default_ttl=3600)

# Tickertape symbol mapping cache
tickertape_symbol_cache = SimpleCache(default_ttl=86400)  # 24 hour TTL


class StockDataProvider(ABC):
    """Abstract base class for stock data providers."""

    name: str = "base"
    is_rate_limited: bool = False
    rate_limit_until: Optional[datetime] = None

    @abstractmethod
    def fetch_stock_data(self, symbol: str, exchange: str = "NSE") -> Optional[Dict[str, Any]]:
        """Fetch stock data for a given symbol."""
        pass

    @abstractmethod
    def search_stocks(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for stocks by name or symbol."""
        pass

    def is_available(self) -> bool:
        """Check if provider is available (not rate limited)."""
        if self.rate_limit_until and datetime.now() < self.rate_limit_until:
            return False
        self.is_rate_limited = False
        return True

    def mark_rate_limited(self, duration_minutes: int = 30):
        """Mark this provider as rate limited."""
        self.is_rate_limited = True
        self.rate_limit_until = datetime.now() + timedelta(minutes=duration_minutes)
        logger.warning(f"{self.name} rate limited for {duration_minutes} minutes")


class YahooFinanceProvider(StockDataProvider):
    """Fetches data from Yahoo Finance via yfinance library."""

    name = "Yahoo Finance"

    def _get_ticker_symbol(self, symbol: str, exchange: str) -> str:
        """Convert to Yahoo Finance format."""
        symbol = symbol.upper().strip().replace(".NS", "").replace(".BO", "")
        if exchange.upper() == "NSE":
            return f"{symbol}{NSE_SUFFIX}"
        elif exchange.upper() == "BSE":
            return f"{symbol}{BSE_SUFFIX}"
        return symbol

    def fetch_stock_data(self, symbol: str, exchange: str = "NSE") -> Optional[Dict[str, Any]]:
        """Fetch stock data from Yahoo Finance."""
        ticker_symbol = self._get_ticker_symbol(symbol, exchange)

        try:
            ticker = yf.Ticker(ticker_symbol)
            info = ticker.info

            if not info or info.get("regularMarketPrice") is None:
                # Try other exchange
                alt_exchange = "BSE" if exchange == "NSE" else "NSE"
                ticker_symbol = self._get_ticker_symbol(symbol, alt_exchange)
                ticker = yf.Ticker(ticker_symbol)
                info = ticker.info

                if not info or info.get("regularMarketPrice") is None:
                    return None

            stock_data = {
                "basic_info": {
                    "company_name": info.get("longName", info.get("shortName", symbol)),
                    "ticker": symbol.upper(),
                    "exchange": exchange,
                    "sector": info.get("sector", "N/A"),
                    "industry": info.get("industry", "N/A"),
                    "website": info.get("website", ""),
                    "description": info.get("longBusinessSummary", ""),
                    "employees": info.get("fullTimeEmployees", 0),
                    "country": info.get("country", "India"),
                },
                "price_info": {
                    "current_price": info.get("regularMarketPrice", info.get("currentPrice", 0)),
                    "previous_close": info.get("previousClose", 0),
                    "open": info.get("regularMarketOpen", info.get("open", 0)),
                    "day_high": info.get("dayHigh", 0),
                    "day_low": info.get("dayLow", 0),
                    "fifty_two_week_high": info.get("fiftyTwoWeekHigh", 0),
                    "fifty_two_week_low": info.get("fiftyTwoWeekLow", 0),
                    "volume": info.get("regularMarketVolume", info.get("volume", 0)),
                },
                "valuation": {
                    "market_cap": info.get("marketCap", 0),
                    "pe_ratio": info.get("trailingPE", info.get("forwardPE", 0)),
                    "pb_ratio": info.get("priceToBook", 0),
                    "dividend_yield": info.get("dividendYield", 0),
                    "eps": info.get("trailingEps", 0),
                    "book_value": info.get("bookValue", 0),
                },
                "financials": {
                    "revenue": info.get("totalRevenue", 0),
                    "profit_margin": info.get("profitMargins", 0),
                    "operating_margin": info.get("operatingMargins", 0),
                    "roe": info.get("returnOnEquity", 0),
                    "roa": info.get("returnOnAssets", 0),
                    "debt_to_equity": info.get("debtToEquity", 0),
                    "current_ratio": info.get("currentRatio", 0),
                },
                "analyst": {
                    "target_price": info.get("targetMeanPrice", 0),
                    "target_high": info.get("targetHighPrice", 0),
                    "target_low": info.get("targetLowPrice", 0),
                    "recommendation": info.get("recommendationKey", ""),
                    "num_analysts": info.get("numberOfAnalystOpinions", 0),
                },
                "provider": self.name,
            }

            return stock_data

        except Exception as e:
            error_msg = str(e).lower()
            if "rate" in error_msg or "too many" in error_msg or "429" in error_msg:
                self.mark_rate_limited(15)  # Reduced from 60 to 15 minutes
                logger.warning(f"Yahoo Finance rate limited: {e}")
            else:
                logger.error(f"Yahoo Finance error for {symbol}: {e}")
            return None

    def search_stocks(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for stocks via Yahoo Finance."""
        try:
            results = []
            return results
        except Exception as e:
            logger.error(f"Yahoo Finance search failed: {e}")
            return []


class TickertapeProvider(StockDataProvider):
    """Fetches data from Tickertape by scraping (has comprehensive fundamentals)."""

    name = "Tickertape"
    BASE_URL = "https://www.tickertape.in"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        })

    def _get_tickertape_slug(self, symbol: str) -> Optional[str]:
        """Get Tickertape URL slug for a symbol."""
        symbol = symbol.upper().strip()

        # Check loaded mapping first
        if symbol in TICKERTAPE_SLUGS:
            return TICKERTAPE_SLUGS[symbol]

        # Check cache for dynamically discovered slugs
        cached = tickertape_symbol_cache.get(f"tt_slug:{symbol}")
        if cached:
            return cached

        # Try Tickertape's autocomplete API first (returns JSON)
        try:
            api_url = f"https://api.tickertape.in/search?text={symbol}"
            response = self.session.get(api_url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get("success") and data.get("data", {}).get("stocks"):
                    stocks = data["data"]["stocks"]
                    for stock in stocks:
                        if stock.get("ticker", "").upper() == symbol:
                            slug = stock.get("slug", "")
                            # Remove '/stocks/' prefix if present
                            if slug.startswith("/stocks/"):
                                slug = slug[8:]
                            if slug:
                                tickertape_symbol_cache.set(f"tt_slug:{symbol}", slug)
                                logger.info(f"Found Tickertape slug for {symbol}: {slug}")
                                return slug
        except Exception as e:
            logger.warning(f"Tickertape API search failed for {symbol}: {e}")

        # Fallback: Try HTML search
        try:
            search_url = f"{self.BASE_URL}/search?text={symbol}"
            response = self.session.get(search_url, timeout=10)

            if response.status_code == 200:
                # Look for stock link in the page
                match = re.search(rf'/stocks/([a-z0-9-]+-[A-Z0-9]+)"', response.text)
                if match:
                    slug = match.group(1)
                    tickertape_symbol_cache.set(f"tt_slug:{symbol}", slug)
                    return slug
        except Exception as e:
            logger.warning(f"Tickertape HTML search failed for {symbol}: {e}")

        return None

    def _parse_json_ld(self, html: str) -> List[Dict]:
        """Extract JSON-LD data from HTML."""
        json_ld_data = []
        try:
            soup = BeautifulSoup(html, 'html.parser')
            scripts = soup.find_all('script', type='application/ld+json')
            for script in scripts:
                try:
                    data = json.loads(script.string)
                    json_ld_data.append(data)
                except:
                    continue
        except Exception as e:
            logger.warning(f"Failed to parse JSON-LD: {e}")
        return json_ld_data

    def _extract_metrics_from_json_ld(self, json_ld_list: List[Dict]) -> Dict[str, Any]:
        """Extract stock metrics from JSON-LD data."""
        metrics = {}

        for data in json_ld_list:
            if isinstance(data, dict):
                # Look for Dataset with metrics
                if data.get("@type") == "Dataset":
                    for item in data.get("mainEntity", []):
                        if isinstance(item, dict):
                            name = item.get("name", "")
                            value = item.get("value", "")
                            if name and value:
                                metrics[name] = value

                # Look for FinancialProduct
                if data.get("@type") == "FinancialProduct":
                    if "offers" in data:
                        offers = data["offers"]
                        if isinstance(offers, dict):
                            metrics["current_price"] = offers.get("price", 0)

        return metrics

    def _parse_float(self, value) -> float:
        """Parse float from various formats."""
        if value is None:
            return 0.0
        try:
            if isinstance(value, (int, float)):
                return float(value)
            # Remove commas, currency symbols, etc.
            cleaned = re.sub(r'[^\d.-]', '', str(value))
            return float(cleaned) if cleaned else 0.0
        except:
            return 0.0

    def fetch_stock_data(self, symbol: str, exchange: str = "NSE") -> Optional[Dict[str, Any]]:
        """Fetch stock data from Tickertape."""
        slug = self._get_tickertape_slug(symbol)
        if not slug:
            logger.warning(f"Tickertape: Could not find slug for {symbol}")
            return None

        try:
            url = f"{self.BASE_URL}/stocks/{slug}"
            response = self.session.get(url, timeout=15)

            if response.status_code == 429:
                self.mark_rate_limited(30)
                return None

            if response.status_code != 200:
                logger.warning(f"Tickertape returned status {response.status_code} for {symbol}")
                return None

            html = response.text

            # Check if we got a valid page (not a block page)
            if "Stock Price" not in html and "Share Price" not in html:
                logger.warning(f"Tickertape returned unexpected content for {symbol}")
                return None

            # Parse JSON-LD data
            json_ld_data = self._parse_json_ld(html)
            metrics = self._extract_metrics_from_json_ld(json_ld_data)

            # Also try to extract from HTML directly using regex
            soup = BeautifulSoup(html, 'html.parser')

            # Extract company name from title
            title = soup.find('title')
            company_name = symbol
            if title:
                title_text = title.get_text()
                if "Share Price" in title_text:
                    company_name = title_text.split(" Share Price")[0].strip()
                elif "Stock Price" in title_text:
                    company_name = title_text.split(" Stock Price")[0].strip()

            # Try to extract key metrics from page
            def extract_metric(pattern: str, text: str) -> Optional[str]:
                match = re.search(pattern, text)
                return match.group(1) if match else None

            # Extract various metrics
            pe_match = re.search(r'"pe"[:\s]*([0-9.]+)', html) or re.search(r'P/E[:\s]*([0-9.]+)', html)
            pb_match = re.search(r'"pb"[:\s]*([0-9.]+)', html) or re.search(r'P/B[:\s]*([0-9.]+)', html)
            market_cap_match = re.search(r'"marketCap"[:\s]*([0-9.]+)', html)
            price_match = re.search(r'"price"[:\s]*([0-9.]+)', html) or re.search(r'"lastPrice"[:\s]*([0-9.]+)', html)

            # Extract sector/industry
            sector_match = re.search(r'"sector"[:\s]*"([^"]+)"', html)
            industry_match = re.search(r'"industry"[:\s]*"([^"]+)"', html)

            stock_data = {
                "basic_info": {
                    "company_name": company_name,
                    "ticker": symbol.upper(),
                    "exchange": exchange,
                    "sector": sector_match.group(1) if sector_match else metrics.get("Sector", "N/A"),
                    "industry": industry_match.group(1) if industry_match else metrics.get("Industry", "N/A"),
                    "website": "",
                    "description": "",
                    "employees": 0,
                    "country": "India",
                },
                "price_info": {
                    "current_price": self._parse_float(price_match.group(1) if price_match else metrics.get("current_price", 0)),
                    "previous_close": 0,
                    "open": 0,
                    "day_high": 0,
                    "day_low": 0,
                    "fifty_two_week_high": 0,
                    "fifty_two_week_low": 0,
                    "volume": 0,
                },
                "valuation": {
                    "market_cap": self._parse_float(market_cap_match.group(1) if market_cap_match else 0),
                    "pe_ratio": self._parse_float(pe_match.group(1) if pe_match else metrics.get("PE Ratio", 0)),
                    "pb_ratio": self._parse_float(pb_match.group(1) if pb_match else metrics.get("PB Ratio", 0)),
                    "dividend_yield": self._parse_float(metrics.get("Dividend Yield", 0)),
                    "eps": 0,
                    "book_value": 0,
                },
                "financials": {
                    "revenue": 0,
                    "profit_margin": 0,
                    "operating_margin": 0,
                    "roe": self._parse_float(metrics.get("ROE", 0)),
                    "roa": 0,
                    "debt_to_equity": self._parse_float(metrics.get("Debt to Equity", 0)),
                    "current_ratio": 0,
                },
                "provider": self.name,
            }

            # Only return if we got at least some meaningful data
            if stock_data["price_info"]["current_price"] > 0 or stock_data["valuation"]["pe_ratio"] > 0:
                return stock_data

            logger.warning(f"Tickertape: No meaningful data extracted for {symbol}")
            return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Tickertape request failed for {symbol}: {e}")
            if "429" in str(e):
                self.mark_rate_limited(30)
            return None
        except Exception as e:
            logger.error(f"Tickertape error for {symbol}: {e}")
            return None

    def search_stocks(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for stocks on Tickertape."""
        try:
            search_url = f"{self.BASE_URL}/search?text={query}"
            response = self.session.get(search_url, timeout=10)

            if response.status_code != 200:
                return []

            results = []
            # Find stock links in search results
            matches = re.findall(r'/stocks/([a-z0-9-]+)-([A-Z]+)"[^>]*>([^<]+)<', response.text)

            for slug_name, ticker_code, name in matches[:limit]:
                results.append({
                    "symbol": ticker_code,
                    "name": name.strip(),
                    "exchange": "NSE",
                })

            return results

        except Exception as e:
            logger.error(f"Tickertape search failed: {e}")
            return []


class GrowwProvider(StockDataProvider):
    """Fetches data from Groww by scraping their stock pages."""

    name = "Groww"
    BASE_URL = "https://groww.in"
    SEARCH_API = "https://groww.in/v1/api/search/v3/query/global/st_query"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        })
        self._slug_cache = SimpleCache(default_ttl=86400)  # 24 hour cache for slugs

    def _get_groww_slug(self, symbol: str) -> Optional[str]:
        """Get Groww URL slug for a symbol using their search API."""
        symbol = symbol.upper().strip()

        # Check cache first
        cached = self._slug_cache.get(f"groww_slug:{symbol}")
        if cached:
            return cached

        try:
            params = {
                "page": 0,
                "query": symbol,
                "size": 10,
                "web": "true"
            }
            response = self.session.get(self.SEARCH_API, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                stocks = data.get("data", {}).get("content", [])

                for stock in stocks:
                    if stock.get("entity_type") == "Stocks":
                        nse_code = stock.get("nse_scrip_code", "").upper()
                        if nse_code == symbol:
                            slug = stock.get("id") or stock.get("search_id")
                            if slug:
                                self._slug_cache.set(f"groww_slug:{symbol}", slug)
                                logger.info(f"Found Groww slug for {symbol}: {slug}")
                                return slug

                # If no exact match, try first stock result
                for stock in stocks:
                    if stock.get("entity_type") == "Stocks":
                        slug = stock.get("id") or stock.get("search_id")
                        if slug:
                            self._slug_cache.set(f"groww_slug:{symbol}", slug)
                            return slug

        except Exception as e:
            logger.warning(f"Groww search API failed for {symbol}: {e}")

        return None

    def _parse_float(self, value) -> float:
        """Parse float from various formats."""
        if value is None:
            return 0.0
        try:
            if isinstance(value, (int, float)):
                return float(value)
            cleaned = re.sub(r'[^\d.-]', '', str(value))
            return float(cleaned) if cleaned else 0.0
        except:
            return 0.0

    def _parse_market_cap(self, value: str) -> float:
        """Parse market cap with Cr/L multipliers."""
        if not value:
            return 0.0
        try:
            value = value.replace(",", "").replace("₹", "").strip()
            multiplier = 1
            if "Cr" in value:
                value = value.replace("Cr", "").strip()
                multiplier = 10000000  # 1 Cr = 10 million
            elif "L" in value:
                value = value.replace("L", "").strip()
                multiplier = 100000  # 1 L = 100k
            return float(value) * multiplier
        except:
            return 0.0

    def fetch_stock_data(self, symbol: str, exchange: str = "NSE") -> Optional[Dict[str, Any]]:
        """Fetch stock data from Groww using Next.js data."""
        slug = self._get_groww_slug(symbol)
        if not slug:
            logger.warning(f"Groww: Could not find slug for {symbol}")
            return None

        try:
            url = f"{self.BASE_URL}/stocks/{slug}"
            response = self.session.get(url, timeout=15)

            if response.status_code == 429:
                self.mark_rate_limited(30)
                return None

            if response.status_code != 200:
                logger.warning(f"Groww returned status {response.status_code} for {symbol}")
                return None

            html = response.text
            soup = BeautifulSoup(html, 'html.parser')

            # Extract data from __NEXT_DATA__ JSON (Next.js)
            next_data_script = soup.find('script', id='__NEXT_DATA__')
            if not next_data_script:
                logger.warning(f"Groww: No __NEXT_DATA__ found for {symbol}")
                return None

            next_data = json.loads(next_data_script.string)
            stock_data = next_data.get('props', {}).get('pageProps', {}).get('stockData', {})

            if not stock_data:
                logger.warning(f"Groww: No stockData in response for {symbol}")
                return None

            data = self._extract_from_next_data(stock_data, symbol, exchange)
            if data:
                data["provider"] = self.name
                return data

            return None

        except Exception as e:
            logger.error(f"Groww error for {symbol}: {e}")
            return None

    def _extract_from_next_data(self, stock_data: Dict, symbol: str, exchange: str) -> Optional[Dict[str, Any]]:
        """Extract stock data from Groww's __NEXT_DATA__ JSON."""
        try:
            header = stock_data.get('header', {})
            stats = stock_data.get('stats', {})
            price_data_raw = stock_data.get('priceData', {})

            # priceData is nested: {nse: {...}, bse: {...}}
            # Prefer NSE data
            price_data = price_data_raw.get('nse', {}) or price_data_raw.get('bse', {})

            company_name = header.get('displayName') or header.get('shortName') or symbol
            industry = header.get('industryName', 'N/A')

            # Get current price from priceData
            current_price = price_data.get('ltp', 0) or price_data.get('close', 0)

            # Build the response in standard format
            result = {
                "basic_info": {
                    "company_name": company_name,
                    "ticker": header.get('nseScriptCode') or symbol.upper(),
                    "exchange": exchange,
                    "sector": industry,
                    "industry": industry,
                    "isin": header.get('isin', ''),
                },
                "price_info": {
                    "current_price": current_price,
                    "previous_close": price_data.get('close', 0),
                    "open": price_data.get('open', 0),
                    "day_high": price_data.get('high', 0),
                    "day_low": price_data.get('low', 0),
                    "volume": price_data.get('volume', 0),
                    "fifty_two_week_high": price_data.get('yearHighPrice', 0),
                    "fifty_two_week_low": price_data.get('yearLowPrice', 0),
                    "day_change": price_data.get('dayChange', 0),
                    "day_change_percent": price_data.get('dayChangePerc', 0),
                },
                "valuation": {
                    "market_cap": stats.get('marketCap', 0) * 10000000,  # Convert Cr to actual
                    "pe_ratio": stats.get('peRatio', 0),
                    "pb_ratio": stats.get('pbRatio', 0),
                    "dividend_yield": stats.get('divYield', 0),
                    "eps": stats.get('epsTtm', 0),
                    "industry_pe": stats.get('industryPe', 0),
                    "ev_to_ebitda": stats.get('evToEbitda', 0),
                    "price_to_sales": stats.get('priceToSales', 0),
                    "peg_ratio": stats.get('pegRatio', 0),
                },
                "financials": {
                    "roe": stats.get('roe', 0),
                    "roce": stats.get('returnOnEquity', 0),
                    "roa": stats.get('returnOnAssets', 0),
                    "debt_to_equity": stats.get('debtToEquity', 0),
                    "book_value": stats.get('bookValue', 0),
                    "face_value": stats.get('faceValue', 0),
                    "operating_margin": stats.get('operatingProfitMargin', 0),
                    "net_profit_margin": stats.get('netProfitMargin', 0),
                    "current_ratio": stats.get('currentRatio', 0),
                },
            }

            # Only return if we got meaningful data
            if current_price > 0 or stats.get('marketCap', 0) > 0:
                return result

            return None

        except Exception as e:
            logger.error(f"Groww data extraction failed: {e}")
            return None

    def search_stocks(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for stocks via Groww."""
        try:
            params = {
                "page": 0,
                "query": query,
                "size": limit,
                "web": "true"
            }
            response = self.session.get(self.SEARCH_API, params=params, timeout=10)

            if response.status_code != 200:
                return []

            data = response.json()
            results = []

            for stock in data.get("data", {}).get("content", []):
                if stock.get("entity_type") == "Stocks":
                    results.append({
                        "symbol": stock.get("nse_scrip_code") or stock.get("bse_scrip_code", ""),
                        "name": stock.get("title", ""),
                        "exchange": "NSE" if stock.get("nse_scrip_code") else "BSE",
                        "isin": stock.get("isin", ""),
                    })

            return results[:limit]

        except Exception as e:
            logger.error(f"Groww search failed: {e}")
            return []


class AlphaVantageProvider(StockDataProvider):
    """Fetches data from Alpha Vantage API (fallback)."""

    name = "Alpha Vantage"
    BASE_URL = "https://www.alphavantage.co/query"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._calls_today = 0
        self._last_call_date = None

    def _check_daily_limit(self) -> bool:
        """Check if we've hit the daily limit (25 for free tier)."""
        today = datetime.now().date()
        if self._last_call_date != today:
            self._calls_today = 0
            self._last_call_date = today
        return self._calls_today < 25

    def _get_symbol(self, symbol: str, exchange: str) -> str:
        """Format symbol for Alpha Vantage (NSE:SYMBOL or BSE:SYMBOL)."""
        symbol = symbol.upper().strip()
        if exchange.upper() == "NSE":
            return f"NSE:{symbol}"
        elif exchange.upper() == "BSE":
            return f"BSE:{symbol}"
        return symbol

    def fetch_stock_data(self, symbol: str, exchange: str = "NSE") -> Optional[Dict[str, Any]]:
        """Fetch stock data from Alpha Vantage."""
        if not self._check_daily_limit():
            logger.warning("Alpha Vantage daily limit reached")
            return None

        av_symbol = self._get_symbol(symbol, exchange)

        try:
            # Get quote data
            params = {
                "function": "GLOBAL_QUOTE",
                "symbol": av_symbol,
                "apikey": self.api_key,
            }

            response = requests.get(self.BASE_URL, params=params, timeout=15)
            self._calls_today += 1

            if response.status_code != 200:
                return None

            data = response.json()

            # Check for rate limit message
            if "Note" in data or "Information" in data:
                self.mark_rate_limited(60)
                return None

            quote = data.get("Global Quote", {})

            if not quote:
                return None

            stock_data = {
                "basic_info": {
                    "company_name": symbol,
                    "ticker": symbol.upper(),
                    "exchange": exchange,
                    "sector": "N/A",
                    "industry": "N/A",
                },
                "price_info": {
                    "current_price": float(quote.get("05. price", 0)),
                    "previous_close": float(quote.get("08. previous close", 0)),
                    "open": float(quote.get("02. open", 0)),
                    "day_high": float(quote.get("03. high", 0)),
                    "day_low": float(quote.get("04. low", 0)),
                    "volume": int(quote.get("06. volume", 0)),
                    "change": float(quote.get("09. change", 0)),
                    "change_percent": quote.get("10. change percent", "0%").replace("%", ""),
                },
                "provider": self.name,
            }

            return stock_data

        except Exception as e:
            logger.error(f"Alpha Vantage error for {symbol}: {e}")
            return None

    def search_stocks(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for stocks via Alpha Vantage."""
        if not self._check_daily_limit():
            return []

        try:
            params = {
                "function": "SYMBOL_SEARCH",
                "keywords": query,
                "apikey": self.api_key,
            }

            response = requests.get(self.BASE_URL, params=params, timeout=10)
            self._calls_today += 1

            if response.status_code != 200:
                return []

            data = response.json()
            results = []

            for match in data.get("bestMatches", [])[:limit]:
                region = match.get("4. region", "")
                if "India" in region:
                    results.append({
                        "symbol": match.get("1. symbol", "").replace("NSE:", "").replace("BSE:", ""),
                        "name": match.get("2. name", ""),
                        "exchange": "NSE" if "NSE" in match.get("1. symbol", "") else "BSE",
                    })

            return results

        except Exception as e:
            logger.error(f"Alpha Vantage search failed: {e}")
            return []


class StockDataManager:
    """
    Manages multiple stock data providers with automatic rotation and fallback.
    """

    def __init__(self, alpha_vantage_key: str = ""):
        # Provider priority order:
        # 1. Yahoo Finance (comprehensive data, may rate limit)
        # 2. Groww (good fundamentals, scraping)
        # 3. Tickertape (good fundamentals, scraping, often rate limited)
        # 4. Alpha Vantage (limited daily calls, fallback)
        self.providers: List[StockDataProvider] = [
            YahooFinanceProvider(),
            GrowwProvider(),
            TickertapeProvider(),
        ]

        if alpha_vantage_key:
            self.providers.append(AlphaVantageProvider(alpha_vantage_key))
            logger.info("Alpha Vantage provider initialized with API key")

        self.cache = stock_cache

    def _get_cache_key(self, symbol: str, exchange: str) -> str:
        """Generate cache key for a stock."""
        return f"stock:{exchange}:{symbol}".lower()

    def fetch_stock_data(self, symbol: str, exchange: str = "NSE") -> Optional[Dict[str, Any]]:
        """
        Fetch stock data with provider rotation and caching.
        Tries each provider in order until one succeeds.
        """
        cache_key = self._get_cache_key(symbol, exchange)

        # Check cache first
        cached = self.cache.get(cache_key)
        if cached:
            logger.info(f"Cache hit for {symbol}")
            return cached

        # Try each provider
        for provider in self.providers:
            if not provider.is_available():
                logger.warning(f"Skipping {provider.name} (rate limited until {provider.rate_limit_until})")
                continue

            logger.warning(f"Trying {provider.name} for {symbol}")

            try:
                data = provider.fetch_stock_data(symbol, exchange)

                if data:
                    # Cache successful response
                    self.cache.set(cache_key, data)
                    logger.warning(f"Success: {provider.name} returned data for {symbol}")
                    return data
                else:
                    logger.warning(f"{provider.name} returned no data for {symbol}")

            except Exception as e:
                logger.error(f"{provider.name} exception for {symbol}: {e}")
                continue

        logger.error(f"All providers failed for {symbol}")
        return None

    def search_stocks(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for stocks across providers."""
        for provider in self.providers:
            if not provider.is_available():
                continue

            results = provider.search_stocks(query, limit)
            if results:
                return results

        return []

    def get_provider_status(self) -> List[Dict[str, Any]]:
        """Get status of all providers."""
        return [
            {
                "name": p.name,
                "available": p.is_available(),
                "rate_limited": p.is_rate_limited,
                "rate_limit_until": p.rate_limit_until.isoformat() if p.rate_limit_until else None,
            }
            for p in self.providers
        ]

    def reset_rate_limits(self):
        """Reset all provider rate limits (admin function)."""
        for provider in self.providers:
            provider.is_rate_limited = False
            provider.rate_limit_until = None
        logger.info("All provider rate limits reset")


# Singleton instance
_manager: Optional[StockDataManager] = None


def get_stock_manager(alpha_vantage_key: str = "") -> StockDataManager:
    """Get or create the stock data manager singleton."""
    global _manager
    if _manager is None:
        _manager = StockDataManager(alpha_vantage_key)
    return _manager
