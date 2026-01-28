"""
Multi-source stock data providers with automatic rotation and fallback.
Providers: NSE India (primary), Yahoo Finance (backup), Alpha Vantage (fallback)
"""

import requests
import yfinance as yf
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from functools import lru_cache
import time
import logging
import hashlib
import json

from config import NSE_SUFFIX, BSE_SUFFIX

logger = logging.getLogger(__name__)

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


class NSEIndiaProvider(StockDataProvider):
    """Fetches data directly from NSE India website."""

    name = "NSE India"
    BASE_URL = "https://www.nseindia.com"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": "https://www.nseindia.com/",
        })
        self._cookies_initialized = False

    def _init_cookies(self):
        """Initialize session cookies by visiting the main page."""
        if self._cookies_initialized:
            return
        try:
            self.session.get(self.BASE_URL, timeout=10)
            self._cookies_initialized = True
        except Exception as e:
            logger.warning(f"Failed to initialize NSE cookies: {e}")

    def _fetch_corporate_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch corporate info (quarterly results, shareholding, actions) from NSE."""
        try:
            corp_url = f"{self.BASE_URL}/api/top-corp-info?symbol={symbol}&market=equities"
            response = self.session.get(corp_url, timeout=10)

            if response.status_code != 200:
                return None

            return response.json()
        except Exception as e:
            logger.warning(f"NSE corporate info fetch failed for {symbol}: {e}")
            return None

    def _parse_quarterly_results(self, financial_data: List[Dict]) -> List[Dict[str, Any]]:
        """Parse quarterly financial results into standardized format."""
        results = []
        for item in financial_data[:8]:  # Last 8 quarters (2 years)
            try:
                results.append({
                    "period_end": item.get("to_date", ""),
                    "revenue": self._parse_number(item.get("income", 0)),
                    "profit_before_tax": self._parse_number(item.get("reProLossBefTax", 0)),
                    "profit_after_tax": self._parse_number(item.get("proLossAftTax", 0)),
                    "eps": self._parse_float(item.get("reDilEPS", 0)),
                    "audited": item.get("audited", ""),
                    "consolidated": item.get("consolidated", ""),
                })
            except Exception:
                continue
        return results

    def _parse_shareholding(self, shareholding_data: Dict) -> Dict[str, Any]:
        """Parse shareholding pattern data."""
        if not shareholding_data:
            return {}

        # Get the most recent quarter
        quarters = sorted(shareholding_data.keys(), reverse=True)
        if not quarters:
            return {}

        latest = quarters[0]
        latest_data = shareholding_data[latest]

        result = {"as_of": latest, "breakdown": {}}
        for item in latest_data:
            for key, value in item.items():
                if key != "Total":
                    result["breakdown"][key] = self._parse_float(value)

        return result

    def _parse_corporate_actions(self, actions_data: List[Dict]) -> List[Dict[str, str]]:
        """Parse corporate actions (dividends, bonuses, splits)."""
        actions = []
        for item in actions_data[:10]:  # Last 10 actions
            actions.append({
                "date": item.get("exdate", ""),
                "action": item.get("purpose", ""),
            })
        return actions

    def _parse_number(self, value) -> int:
        """Parse numeric value, handling None and strings."""
        if value is None:
            return 0
        try:
            return int(str(value).replace(",", "").strip())
        except (ValueError, TypeError):
            return 0

    def _parse_float(self, value) -> float:
        """Parse float value, handling None and strings."""
        if value is None:
            return 0.0
        try:
            return float(str(value).replace(",", "").strip())
        except (ValueError, TypeError):
            return 0.0

    def fetch_stock_data(self, symbol: str, exchange: str = "NSE") -> Optional[Dict[str, Any]]:
        """Fetch stock data from NSE India."""
        if exchange.upper() != "NSE":
            return None  # NSE India only supports NSE

        self._init_cookies()
        symbol = symbol.upper().strip()

        try:
            # Fetch quote data
            quote_url = f"{self.BASE_URL}/api/quote-equity?symbol={symbol}"
            response = self.session.get(quote_url, timeout=15)

            if response.status_code == 429:
                self.mark_rate_limited(30)
                return None

            if response.status_code != 200:
                return None

            data = response.json()

            if not data or "info" not in data:
                return None

            info = data.get("info", {})
            metadata = data.get("metadata", {})
            price_info = data.get("priceInfo", {})
            security_info = data.get("securityInfo", {})
            industry_info = data.get("industryInfo", {})

            # Build standardized response
            stock_data = {
                "basic_info": {
                    "company_name": info.get("companyName", symbol),
                    "ticker": symbol,
                    "exchange": "NSE",
                    "sector": industry_info.get("sector", metadata.get("pdSectorInd", "N/A")),
                    "industry": industry_info.get("industry", info.get("industry", "N/A")),
                    "website": "",
                    "description": "",
                    "employees": 0,
                    "country": "India",
                    "isin": info.get("isin", ""),
                },
                "price_info": {
                    "current_price": price_info.get("lastPrice", 0),
                    "previous_close": price_info.get("previousClose", 0),
                    "open": price_info.get("open", 0),
                    "day_high": price_info.get("intraDayHighLow", {}).get("max", 0),
                    "day_low": price_info.get("intraDayHighLow", {}).get("min", 0),
                    "fifty_two_week_high": price_info.get("weekHighLow", {}).get("max", 0),
                    "fifty_two_week_low": price_info.get("weekHighLow", {}).get("min", 0),
                    "change": price_info.get("change", 0),
                    "change_percent": price_info.get("pChange", 0),
                    "vwap": price_info.get("vwap", 0),
                },
                "valuation": {
                    "market_cap": 0,  # Not directly available, calculate if needed
                    "pe_ratio": metadata.get("pdSymbolPe", 0),
                    "sector_pe": metadata.get("pdSectorPe", 0),
                    "face_value": security_info.get("faceValue", 0),
                    "issued_size": security_info.get("issuedSize", 0),
                },
                "trading_info": {
                    "volume": 0,  # Would need trade info endpoint
                    "upper_circuit": price_info.get("upperCP", ""),
                    "lower_circuit": price_info.get("lowerCP", ""),
                    "listing_date": metadata.get("listingDate", ""),
                    "is_fno": info.get("isFNOSec", False),
                },
                "provider": self.name,
            }

            # Fetch corporate info (quarterly results, shareholding, actions)
            # This is a secondary call - don't fail if it doesn't work
            corp_info = self._fetch_corporate_info(symbol)
            if corp_info:
                # Quarterly financial results
                fin_results = corp_info.get("financial_results", {}).get("data", [])
                if fin_results:
                    stock_data["quarterly_results"] = self._parse_quarterly_results(fin_results)

                # Shareholding pattern
                shareholding = corp_info.get("shareholdings_patterns", {}).get("data", {})
                if shareholding:
                    stock_data["shareholding"] = self._parse_shareholding(shareholding)

                # Corporate actions (dividends, bonuses)
                actions = corp_info.get("corporate_actions", {}).get("data", [])
                if actions:
                    stock_data["corporate_actions"] = self._parse_corporate_actions(actions)

                # Latest announcements (just the subjects)
                announcements = corp_info.get("latest_announcements", {}).get("data", [])
                if announcements:
                    stock_data["recent_announcements"] = [
                        {
                            "date": a.get("broadcastdate", ""),
                            "subject": a.get("subject", ""),
                        }
                        for a in announcements[:5]  # Last 5 announcements
                    ]

            return stock_data

        except requests.exceptions.RequestException as e:
            logger.error(f"NSE India request failed for {symbol}: {e}")
            if "429" in str(e) or "rate" in str(e).lower():
                self.mark_rate_limited(30)
            return None
        except Exception as e:
            logger.error(f"NSE India error for {symbol}: {e}")
            return None

    def search_stocks(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for stocks on NSE."""
        self._init_cookies()

        try:
            search_url = f"{self.BASE_URL}/api/search/autocomplete?q={query}"
            response = self.session.get(search_url, timeout=10)

            if response.status_code != 200:
                return []

            data = response.json()
            results = []

            for item in data.get("symbols", [])[:limit]:
                results.append({
                    "symbol": item.get("symbol", ""),
                    "name": item.get("symbol_info", ""),
                    "exchange": "NSE",
                })

            return results

        except Exception as e:
            logger.error(f"NSE India search failed: {e}")
            return []


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
                self.mark_rate_limited(60)
                logger.warning(f"Yahoo Finance rate limited: {e}")
            else:
                logger.error(f"Yahoo Finance error for {symbol}: {e}")
            return None

    def search_stocks(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for stocks via Yahoo Finance."""
        try:
            # Use yfinance search (limited functionality)
            results = []
            # Yahoo doesn't have great search, return empty and let other providers handle it
            return results
        except Exception as e:
            logger.error(f"Yahoo Finance search failed: {e}")
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
                    "company_name": symbol,  # Alpha Vantage doesn't return company name in quote
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
                # Filter for Indian stocks
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
        self.providers: List[StockDataProvider] = [
            NSEIndiaProvider(),
            YahooFinanceProvider(),
        ]

        if alpha_vantage_key:
            self.providers.append(AlphaVantageProvider(alpha_vantage_key))

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
                logger.info(f"Skipping {provider.name} (rate limited)")
                continue

            logger.info(f"Trying {provider.name} for {symbol}")

            try:
                data = provider.fetch_stock_data(symbol, exchange)

                if data:
                    # Cache successful response
                    self.cache.set(cache_key, data)
                    logger.info(f"Success: {provider.name} returned data for {symbol}")
                    return data

            except Exception as e:
                logger.error(f"{provider.name} failed for {symbol}: {e}")
                continue

        logger.warning(f"All providers failed for {symbol}")
        return None

    def search_stocks(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for stocks across providers."""
        # Try NSE India first (best for Indian stocks)
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


# Singleton instance
_manager: Optional[StockDataManager] = None


def get_stock_manager(alpha_vantage_key: str = "") -> StockDataManager:
    """Get or create the stock data manager singleton."""
    global _manager
    if _manager is None:
        _manager = StockDataManager(alpha_vantage_key)
    return _manager
