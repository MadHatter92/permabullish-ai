import yfinance as yf
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from pathlib import Path
import json
import logging

from config import NSE_SUFFIX, BSE_SUFFIX, ALPHA_VANTAGE_API_KEY
from stock_providers import get_stock_manager, StockDataManager

logger = logging.getLogger(__name__)


# Cache for stock list
_stock_list_cache: Optional[List[Dict]] = None


def _load_stock_list() -> List[Dict]:
    """Load stock list from JSON file (prefers expanded NSE list, falls back to Nifty 500)."""
    global _stock_list_cache
    if _stock_list_cache is not None:
        return _stock_list_cache

    try:
        # Try expanded list first (1900 stocks), fall back to Nifty 500
        data_file = Path(__file__).parent / "data" / "nse_eq_stocks.json"
        if not data_file.exists():
            data_file = Path(__file__).parent / "data" / "nifty500_stocks.json"

        with open(data_file, 'r') as f:
            stocks = json.load(f)
        # Convert to search format
        _stock_list_cache = [
            {
                "symbol": s["symbol"],
                "name": s.get("company_name", s["symbol"]),
                "sector": s.get("industry", "")
            }
            for s in stocks
        ]
        logger.info(f"Loaded {len(_stock_list_cache)} stocks for search")
        return _stock_list_cache
    except Exception as e:
        logger.error(f"Failed to load stock list: {e}")
        return []

# Initialize the multi-provider stock data manager
_stock_manager: Optional[StockDataManager] = None


def get_manager() -> StockDataManager:
    """Get or create the stock data manager singleton."""
    global _stock_manager
    if _stock_manager is None:
        _stock_manager = get_stock_manager(ALPHA_VANTAGE_API_KEY)
    return _stock_manager


def get_ticker_symbol(symbol: str, exchange: str = "NSE") -> str:
    """Convert symbol to Yahoo Finance format for Indian stocks."""
    symbol = symbol.upper().strip()
    # Remove any existing suffix
    symbol = symbol.replace(".NS", "").replace(".BO", "")

    if exchange.upper() == "NSE":
        return f"{symbol}{NSE_SUFFIX}"
    elif exchange.upper() == "BSE":
        return f"{symbol}{BSE_SUFFIX}"
    return symbol


def fetch_stock_data(symbol: str, exchange: str = "NSE") -> Optional[Dict[str, Any]]:
    """
    Fetch comprehensive stock data using multi-provider rotation.
    Primary: NSE India direct, Backup: Yahoo Finance, Fallback: Alpha Vantage.
    Returns structured data for report generation.
    """
    manager = get_manager()

    # Try to get basic data from the provider rotation
    basic_data = manager.fetch_stock_data(symbol, exchange)

    if not basic_data:
        logger.warning(f"All providers failed for {symbol}")
        return None

    # If we got data from NSE India or Alpha Vantage,
    # try to enrich with Yahoo Finance for detailed fundamentals
    provider = basic_data.get("provider", "")

    if provider != "Yahoo Finance":
        # Try to get additional data from Yahoo Finance
        try:
            yahoo_data = _fetch_yahoo_enrichment(symbol, exchange)
            if yahoo_data:
                basic_data = _merge_stock_data(basic_data, yahoo_data)
        except Exception as e:
            logger.warning(f"Yahoo enrichment failed for {symbol}: {e}")

    return basic_data


def _fetch_yahoo_enrichment(symbol: str, exchange: str) -> Optional[Dict[str, Any]]:
    """Fetch additional data from Yahoo Finance for enrichment."""
    ticker_symbol = get_ticker_symbol(symbol, exchange)

    try:
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info

        if not info or info.get("regularMarketPrice") is None:
            return None

        # Get historical data for charts
        hist = ticker.history(period="1y")

        # Get financials
        financials = ticker.financials
        quarterly_financials = ticker.quarterly_financials

        # Get latest news
        try:
            news = ticker.news[:10] if ticker.news else []
        except:
            news = []

        enrichment_data = {
            "basic_info": {
                "description": info.get("longBusinessSummary", ""),
                "website": info.get("website", ""),
                "employees": info.get("fullTimeEmployees", 0),
            },
            "valuation": {
                "market_cap": info.get("marketCap", 0),
                "enterprise_value": info.get("enterpriseValue", 0),
                "pe_ratio": info.get("trailingPE", info.get("forwardPE", 0)),
                "forward_pe": info.get("forwardPE", 0),
                "peg_ratio": info.get("pegRatio", 0),
                "pb_ratio": info.get("priceToBook", 0),
                "ps_ratio": info.get("priceToSalesTrailing12Months", 0),
                "ev_to_ebitda": info.get("enterpriseToEbitda", 0),
                "ev_to_revenue": info.get("enterpriseToRevenue", 0),
            },
            "financials": {
                "revenue": info.get("totalRevenue", 0),
                "revenue_growth": info.get("revenueGrowth", 0),
                "gross_profit": info.get("grossProfits", 0),
                "ebitda": info.get("ebitda", 0),
                "operating_income": info.get("operatingIncome", 0),
                "net_income": info.get("netIncomeToCommon", 0),
                "profit_margin": info.get("profitMargins", 0),
                "operating_margin": info.get("operatingMargins", 0),
                "gross_margin": info.get("grossMargins", 0),
                "ebitda_margin": info.get("ebitdaMargins", 0),
            },
            "per_share": {
                "eps": info.get("trailingEps", 0),
                "forward_eps": info.get("forwardEps", 0),
                "book_value": info.get("bookValue", 0),
                "revenue_per_share": info.get("revenuePerShare", 0),
            },
            "dividends": {
                "dividend_rate": info.get("dividendRate", 0),
                "dividend_yield": info.get("dividendYield", 0),
                "payout_ratio": info.get("payoutRatio", 0),
                "ex_dividend_date": info.get("exDividendDate", None),
            },
            "balance_sheet": {
                "total_cash": info.get("totalCash", 0),
                "total_debt": info.get("totalDebt", 0),
                "debt_to_equity": info.get("debtToEquity", 0),
                "current_ratio": info.get("currentRatio", 0),
                "quick_ratio": info.get("quickRatio", 0),
                "total_assets": info.get("totalAssets", 0),
                "total_liabilities": info.get("totalLiabilities", 0),
            },
            "returns": {
                "roe": info.get("returnOnEquity", 0),
                "roa": info.get("returnOnAssets", 0),
            },
            "ownership": {
                "insider_holding": info.get("heldPercentInsiders", 0),
                "institution_holding": info.get("heldPercentInstitutions", 0),
            },
            "analyst_data": {
                "target_mean_price": info.get("targetMeanPrice", 0),
                "target_high_price": info.get("targetHighPrice", 0),
                "target_low_price": info.get("targetLowPrice", 0),
                "recommendation": info.get("recommendationKey", ""),
                "num_analysts": info.get("numberOfAnalystOpinions", 0),
            },
        }

        # Process historical financials if available
        if financials is not None and not financials.empty:
            enrichment_data["historical_financials"] = process_financials(financials)

        # Process quarterly financials
        if quarterly_financials is not None and not quarterly_financials.empty:
            enrichment_data["quarterly_results"] = process_quarterly_financials(quarterly_financials)

        # Add news
        enrichment_data["recent_news"] = []
        for article in news:
            try:
                enrichment_data["recent_news"].append({
                    "title": article.get("title", ""),
                    "publisher": article.get("publisher", ""),
                    "link": article.get("link", ""),
                    "published": article.get("providerPublishTime", 0),
                    "type": article.get("type", ""),
                })
            except:
                pass

        # Get historical prices for charts
        if not hist.empty:
            enrichment_data["price_history"] = {
                "dates": hist.index.strftime("%Y-%m-%d").tolist()[-252:],
                "prices": hist["Close"].tolist()[-252:],
                "volumes": hist["Volume"].tolist()[-252:],
            }

        return enrichment_data

    except Exception as e:
        logger.warning(f"Yahoo enrichment error for {symbol}: {e}")
        return None


def _merge_stock_data(primary: Dict[str, Any], enrichment: Dict[str, Any]) -> Dict[str, Any]:
    """Merge enrichment data into primary data, preferring primary for conflicts."""
    result = primary.copy()

    for key, value in enrichment.items():
        if key not in result:
            result[key] = value
        elif isinstance(value, dict) and isinstance(result.get(key), dict):
            # Merge nested dicts, preferring values from primary
            for sub_key, sub_value in value.items():
                if sub_key not in result[key] or not result[key][sub_key]:
                    result[key][sub_key] = sub_value
        elif isinstance(value, list) and not result.get(key):
            result[key] = value

    return result


def process_financials(df) -> Dict[str, Dict[str, float]]:
    """Process financials DataFrame into a clean dictionary."""
    result = {}
    for col in df.columns:
        year = col.strftime("%Y") if hasattr(col, "strftime") else str(col)
        result[year] = {}
        for idx in df.index:
            value = df.loc[idx, col]
            if value is not None and not (isinstance(value, float) and value != value):  # Check for NaN
                result[year][str(idx)] = float(value)
    return result


def process_quarterly_financials(df) -> list:
    """Process quarterly financials into a list of quarter results."""
    quarters = []
    for col in df.columns[:4]:  # Last 4 quarters
        quarter_data = {
            "period": col.strftime("%b %Y") if hasattr(col, "strftime") else str(col),
        }
        for idx in df.index:
            value = df.loc[idx, col]
            if value is not None and not (isinstance(value, float) and value != value):
                # Clean up the key name
                key = str(idx).replace(" ", "_").lower()
                quarter_data[key] = float(value)
        quarters.append(quarter_data)
    return quarters


def search_stocks(query: str, limit: int = 10) -> list:
    """
    Search for Indian stocks matching the query.
    Returns list of matching tickers from Nifty 500.
    """
    indian_stocks = _load_stock_list()

    # Fallback to minimal list if JSON loading fails
    if not indian_stocks:
        indian_stocks = [
            {"symbol": "RELIANCE", "name": "Reliance Industries", "sector": "Oil & Gas"},
            {"symbol": "TCS", "name": "Tata Consultancy Services", "sector": "IT"},
            {"symbol": "HDFCBANK", "name": "HDFC Bank", "sector": "Banking"},
            {"symbol": "INFY", "name": "Infosys", "sector": "IT"},
            {"symbol": "ICICIBANK", "name": "ICICI Bank", "sector": "Banking"},
        ]

    query = query.upper()
    results = []

    for stock in indian_stocks:
        symbol_match = query in stock["symbol"].upper()
        name_match = query.lower() in stock["name"].lower()
        if symbol_match or name_match:
            results.append(stock)
            if len(results) >= limit:
                break

    return results


def format_indian_number(num: float) -> str:
    """Format number in Indian style (lakhs, crores)."""
    if num is None or num == 0:
        return "0"

    abs_num = abs(num)
    sign = "-" if num < 0 else ""

    if abs_num >= 1e7:  # Crores
        return f"{sign}{abs_num/1e7:.2f} Cr"
    elif abs_num >= 1e5:  # Lakhs
        return f"{sign}{abs_num/1e5:.2f} L"
    elif abs_num >= 1e3:  # Thousands
        return f"{sign}{abs_num/1e3:.2f} K"
    else:
        return f"{sign}{abs_num:.2f}"


def format_market_cap(market_cap: float) -> str:
    """Format market cap in Indian style."""
    if market_cap is None or market_cap == 0:
        return "N/A"

    if market_cap >= 1e12:  # Lakh Crores
        return f"₹{market_cap/1e12:.2f}L Cr"
    elif market_cap >= 1e9:  # Thousand Crores
        return f"₹{market_cap/1e7:.0f} Cr"
    elif market_cap >= 1e7:  # Crores
        return f"₹{market_cap/1e7:.2f} Cr"
    else:
        return f"₹{market_cap/1e5:.2f} L"


def calculate_upside(current_price: float, target_price: float) -> float:
    """Calculate upside percentage."""
    if current_price and target_price and current_price > 0:
        return ((target_price - current_price) / current_price) * 100
    return 0
