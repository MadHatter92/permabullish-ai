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
    """Load stock list from JSON files, merging NSE list with Nifty 500 names."""
    global _stock_list_cache
    if _stock_list_cache is not None:
        return _stock_list_cache

    try:
        data_dir = Path(__file__).parent / "data"

        # Load Nifty 500 first (has proper company names)
        nifty_names = {}
        nifty_file = data_dir / "nifty500_stocks.json"
        if nifty_file.exists():
            with open(nifty_file, 'r') as f:
                nifty_stocks = json.load(f)
                for s in nifty_stocks:
                    nifty_names[s["symbol"]] = {
                        "name": s.get("company_name", s["symbol"]),
                        "sector": s.get("industry", "")
                    }

        # Load expanded NSE list
        nse_file = data_dir / "nse_eq_stocks.json"
        if nse_file.exists():
            with open(nse_file, 'r') as f:
                stocks = json.load(f)
        elif nifty_file.exists():
            stocks = nifty_stocks
        else:
            stocks = []

        # Convert to search format, preferring Nifty 500 names when available
        _stock_list_cache = []
        for s in stocks:
            symbol = s["symbol"]
            if symbol in nifty_names:
                # Use proper name from Nifty 500
                _stock_list_cache.append({
                    "symbol": symbol,
                    "name": nifty_names[symbol]["name"],
                    "sector": nifty_names[symbol]["sector"] or s.get("industry", "")
                })
            else:
                # Use NSE data (name might just be symbol)
                _stock_list_cache.append({
                    "symbol": symbol,
                    "name": s.get("company_name", symbol),
                    "sector": s.get("industry", "")
                })

        logger.info(f"Loaded {len(_stock_list_cache)} stocks for search ({len(nifty_names)} with full names)")
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
    Also enriches with cached fundamentals from Screener if available.
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

    # Enrich with cached fundamentals from Screener (if available)
    try:
        screener_data = _get_screener_fundamentals(symbol)
        if screener_data:
            basic_data = _merge_screener_data(basic_data, screener_data)
            logger.info(f"Enriched {symbol} with cached Screener data")
    except Exception as e:
        logger.warning(f"Screener enrichment failed for {symbol}: {e}")

    return basic_data


def _get_screener_fundamentals(symbol: str) -> Optional[Dict[str, Any]]:
    """Get cached fundamentals from Screener data in database."""
    try:
        import database as db
        return db.get_cached_fundamentals(symbol)
    except Exception as e:
        logger.warning(f"Failed to get cached fundamentals for {symbol}: {e}")
        return None


def _merge_screener_data(primary: Dict[str, Any], screener: Dict[str, Any]) -> Dict[str, Any]:
    """Merge Screener fundamentals into primary stock data."""
    result = primary.copy()

    # Add Screener-specific data that Yahoo doesn't have
    screener_additions = {
        "screener_data": {
            "quarterly_results": screener.get("quarterly_results", []),
            "profit_loss": screener.get("profit_loss", []),
            "balance_sheet": screener.get("balance_sheet", []),
            "cash_flow": screener.get("cash_flow", []),
            "shareholding": screener.get("shareholding", []),
            "pros": screener.get("pros", []),
            "cons": screener.get("cons", []),
            "source_url": screener.get("source_url", ""),
            "last_updated": str(screener.get("last_updated", "")),
        }
    }

    result.update(screener_additions)

    # Also update key ratios if missing from primary data
    if "valuation" not in result:
        result["valuation"] = {}

    valuation = result["valuation"]

    # Fill in missing valuation metrics from Screener
    if not valuation.get("pe_ratio") and screener.get("pe_ratio"):
        valuation["pe_ratio"] = screener["pe_ratio"]
    if not valuation.get("pb_ratio") and screener.get("pb_ratio"):
        valuation["pb_ratio"] = screener["pb_ratio"]

    # Add returns metrics from Screener
    if "returns" not in result:
        result["returns"] = {}

    returns = result["returns"]
    if not returns.get("roe") and screener.get("roe"):
        returns["roe"] = screener["roe"] / 100 if screener["roe"] > 1 else screener["roe"]
    if not returns.get("roce") and screener.get("roce"):
        returns["roce"] = screener["roce"] / 100 if screener["roce"] > 1 else screener["roce"]

    # Add dividend yield if missing
    if "dividends" not in result:
        result["dividends"] = {}
    if not result["dividends"].get("dividend_yield") and screener.get("dividend_yield"):
        result["dividends"]["dividend_yield"] = screener["dividend_yield"] / 100 if screener["dividend_yield"] > 1 else screener["dividend_yield"]

    return result


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


def fetch_chart_data(symbol: str, exchange: str = "NSE", period: str = "1y") -> Optional[Dict[str, Any]]:
    """
    Fetch historical price data for charts.

    Args:
        symbol: Stock ticker symbol
        exchange: Exchange (NSE or BSE)
        period: Time period - 1m, 3m, 6m, 1y, 5y

    Returns:
        Dictionary with OHLC data, volume, and calculated indicators
    """
    ticker_symbol = get_ticker_symbol(symbol, exchange)

    # Map period to yfinance format
    period_map = {
        "1m": "1mo",
        "3m": "3mo",
        "6m": "6mo",
        "1y": "1y",
        "5y": "5y",
        "max": "max"
    }
    yf_period = period_map.get(period, "1y")

    try:
        ticker = yf.Ticker(ticker_symbol)
        hist = ticker.history(period=yf_period)

        if hist.empty:
            logger.warning(f"No historical data for {symbol}")
            return None

        # Convert to list format for frontend
        dates = hist.index.strftime("%Y-%m-%d").tolist()
        closes = hist["Close"].tolist()
        highs = hist["High"].tolist()
        lows = hist["Low"].tolist()
        opens = hist["Open"].tolist()
        volumes = hist["Volume"].tolist()

        # Calculate moving averages
        ma50 = []
        ma200 = []

        for i in range(len(closes)):
            # 50-day MA
            if i >= 49:
                ma50.append({
                    "time": dates[i],
                    "value": round(sum(closes[i-49:i+1]) / 50, 2)
                })

            # 200-day MA
            if i >= 199:
                ma200.append({
                    "time": dates[i],
                    "value": round(sum(closes[i-199:i+1]) / 200, 2)
                })

        # Calculate 52-week high/low (use last 252 trading days or all available)
        lookback = min(252, len(closes))
        recent_highs = highs[-lookback:]
        recent_lows = lows[-lookback:]
        week52_high = max(recent_highs) if recent_highs else None
        week52_low = min(recent_lows) if recent_lows else None

        # Calculate period return
        if len(closes) >= 2:
            period_return = ((closes[-1] - closes[0]) / closes[0]) * 100
        else:
            period_return = 0

        # Format price data for Lightweight Charts
        price_data = []
        for i in range(len(dates)):
            price_data.append({
                "time": dates[i],
                "value": round(closes[i], 2)
            })

        # Current price and MAs for footer display
        current_price = round(closes[-1], 2) if closes else None
        current_ma50 = round(ma50[-1]["value"], 2) if ma50 else None
        current_ma200 = round(ma200[-1]["value"], 2) if ma200 else None

        return {
            "symbol": symbol,
            "exchange": exchange,
            "period": period,
            "price_data": price_data,
            "ma50": ma50,
            "ma200": ma200,
            "stats": {
                "current_price": current_price,
                "week52_high": round(week52_high, 2) if week52_high else None,
                "week52_low": round(week52_low, 2) if week52_low else None,
                "ma50": current_ma50,
                "ma200": current_ma200,
                "period_return": round(period_return, 2),
                "data_points": len(price_data)
            }
        }

    except Exception as e:
        logger.error(f"Failed to fetch chart data for {symbol}: {e}")
        return None
