"""
Financial Modeling Prep (FMP) API client for US stock fundamentals.
Free tier: 250 requests/day. Provides income statements, balance sheets,
cash flows, ratios, key metrics, institutional holders, and news.
"""

import requests
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from config import FMP_API_KEY

logger = logging.getLogger(__name__)

BASE_URL = "https://financialmodelingprep.com/api/v3"

# Track daily API calls
_calls_today = 0
_last_call_date = None
DAILY_LIMIT = 245  # Leave some buffer from 250


def _check_daily_limit() -> bool:
    """Check if we've hit the daily API call limit."""
    global _calls_today, _last_call_date
    today = datetime.now().date()
    if _last_call_date != today:
        _calls_today = 0
        _last_call_date = today
    return _calls_today < DAILY_LIMIT


def _make_request(endpoint: str, params: Optional[Dict] = None) -> Optional[Any]:
    """Make a request to the FMP API."""
    global _calls_today

    if not FMP_API_KEY:
        logger.warning("FMP_API_KEY not set, skipping FMP request")
        return None

    if not _check_daily_limit():
        logger.warning("FMP daily API limit reached")
        return None

    if params is None:
        params = {}
    params["apikey"] = FMP_API_KEY

    try:
        url = f"{BASE_URL}/{endpoint}"
        response = requests.get(url, params=params, timeout=15)
        _calls_today += 1

        if response.status_code == 429:
            logger.warning("FMP rate limited")
            return None

        if response.status_code != 200:
            logger.warning(f"FMP returned status {response.status_code} for {endpoint}")
            return None

        data = response.json()

        # FMP returns error messages as dicts
        if isinstance(data, dict) and "Error Message" in data:
            logger.warning(f"FMP error: {data['Error Message']}")
            return None

        return data

    except Exception as e:
        logger.error(f"FMP request failed for {endpoint}: {e}")
        return None


def get_company_profile(symbol: str) -> Optional[Dict[str, Any]]:
    """Get company profile including sector, industry, description."""
    data = _make_request(f"profile/{symbol}")
    if data and isinstance(data, list) and len(data) > 0:
        return data[0]
    return None


def get_income_statement(symbol: str, period: str = "quarter", limit: int = 4) -> Optional[List[Dict]]:
    """Get income statement (quarterly or annual)."""
    data = _make_request(f"income-statement/{symbol}", {"period": period, "limit": limit})
    if data and isinstance(data, list):
        return data
    return None


def get_balance_sheet(symbol: str, period: str = "quarter", limit: int = 4) -> Optional[List[Dict]]:
    """Get balance sheet (quarterly or annual)."""
    data = _make_request(f"balance-sheet-statement/{symbol}", {"period": period, "limit": limit})
    if data and isinstance(data, list):
        return data
    return None


def get_cash_flow(symbol: str, period: str = "quarter", limit: int = 4) -> Optional[List[Dict]]:
    """Get cash flow statement (quarterly or annual)."""
    data = _make_request(f"cash-flow-statement/{symbol}", {"period": period, "limit": limit})
    if data and isinstance(data, list):
        return data
    return None


def get_ratios(symbol: str, period: str = "quarter", limit: int = 4) -> Optional[List[Dict]]:
    """Get financial ratios (PE, PB, ROE, margins, etc.)."""
    data = _make_request(f"ratios/{symbol}", {"period": period, "limit": limit})
    if data and isinstance(data, list):
        return data
    return None


def get_key_metrics(symbol: str, period: str = "quarter", limit: int = 4) -> Optional[List[Dict]]:
    """Get key metrics (EV/EBITDA, market cap, etc.)."""
    data = _make_request(f"key-metrics/{symbol}", {"period": period, "limit": limit})
    if data and isinstance(data, list):
        return data
    return None


def get_institutional_holders(symbol: str) -> Optional[List[Dict]]:
    """Get institutional holders (from 13F filings)."""
    data = _make_request(f"institutional-holder/{symbol}")
    if data and isinstance(data, list):
        return data[:20]  # Top 20 holders
    return None


def get_stock_news(symbol: str, limit: int = 10) -> Optional[List[Dict]]:
    """Get recent stock news."""
    data = _make_request("stock_news", {"tickers": symbol, "limit": limit})
    if data and isinstance(data, list):
        return data
    return None


def get_quote(symbol: str) -> Optional[Dict[str, Any]]:
    """Get real-time stock quote."""
    data = _make_request(f"quote/{symbol}")
    if data and isinstance(data, list) and len(data) > 0:
        return data[0]
    return None


def fetch_us_fundamentals(symbol: str) -> Optional[Dict[str, Any]]:
    """
    Fetch comprehensive US stock fundamentals from FMP.
    Returns data in a structure compatible with the stock_fundamentals table.
    """
    if not FMP_API_KEY:
        return None

    profile = get_company_profile(symbol)
    if not profile:
        logger.warning(f"FMP: No profile found for {symbol}")
        return None

    # Fetch all data (5 API calls total)
    income = get_income_statement(symbol, period="quarter", limit=8)
    balance = get_balance_sheet(symbol, period="quarter", limit=4)
    cash_flow = get_cash_flow(symbol, period="quarter", limit=4)
    ratios = get_ratios(symbol, period="quarter", limit=4)

    # Build fundamentals dict compatible with stock_fundamentals table
    latest_ratios = ratios[0] if ratios else {}

    fundamentals = {
        "symbol": symbol,
        "company_name": profile.get("companyName", symbol),
        "sector": profile.get("sector", ""),
        "industry": profile.get("industry", ""),
        "market_cap": profile.get("mktCap", 0),
        "current_price": profile.get("price", 0),
        "pe_ratio": latest_ratios.get("priceEarningsRatio", profile.get("pe", 0)),
        "pb_ratio": latest_ratios.get("priceToBookRatio", 0),
        "dividend_yield": latest_ratios.get("dividendYield", 0),
        "roe": latest_ratios.get("returnOnEquity", 0),
        "roce": latest_ratios.get("returnOnCapitalEmployed", 0),  # Maps to ROIC for US
        "book_value": profile.get("bookValuePerShare", 0),
        "quarterly_results": _format_fmp_quarterly(income) if income else [],
        "profit_loss": _format_fmp_profit_loss(income) if income else [],
        "balance_sheet": _format_fmp_balance_sheet(balance) if balance else [],
        "cash_flow": _format_fmp_cash_flow(cash_flow) if cash_flow else [],
        "ratios": latest_ratios,
        "source_url": f"https://financialmodelingprep.com/financial-statements/{symbol}",
        "last_updated": datetime.now().isoformat(),
    }

    return fundamentals


def _format_fmp_quarterly(income_data: List[Dict]) -> List[Dict]:
    """Format FMP income statement data into quarterly results format."""
    if not income_data:
        return []

    # Extract key metrics per quarter
    metrics = {}
    for q in income_data[:8]:  # Last 8 quarters
        period = q.get("date", "")[:7]  # YYYY-MM format
        if not period:
            continue

        if "Sales" not in metrics:
            metrics["Sales"] = {"metric": "Sales"}
        metrics["Sales"][period] = q.get("revenue", 0) / 1e6  # Convert to millions

        if "Operating Profit" not in metrics:
            metrics["Operating Profit"] = {"metric": "Operating Profit"}
        metrics["Operating Profit"][period] = q.get("operatingIncome", 0) / 1e6

        if "Net Profit" not in metrics:
            metrics["Net Profit"] = {"metric": "Net Profit"}
        metrics["Net Profit"][period] = q.get("netIncome", 0) / 1e6

        if "EPS" not in metrics:
            metrics["EPS"] = {"metric": "EPS"}
        metrics["EPS"][period] = q.get("eps", 0)

    return list(metrics.values())


def _format_fmp_profit_loss(income_data: List[Dict]) -> List[Dict]:
    """Format FMP data into profit & loss format matching Screener structure."""
    return _format_fmp_quarterly(income_data)


def _format_fmp_balance_sheet(balance_data: List[Dict]) -> List[Dict]:
    """Format FMP balance sheet data."""
    if not balance_data:
        return []

    metrics = {}
    for q in balance_data[:4]:
        period = q.get("date", "")[:7]
        if not period:
            continue

        for key, metric_name in [
            ("totalAssets", "Total Assets"),
            ("totalLiabilities", "Total Liabilities"),
            ("totalStockholdersEquity", "Equity"),
            ("totalDebt", "Borrowings"),
            ("cashAndCashEquivalents", "Cash & Equivalents"),
        ]:
            if metric_name not in metrics:
                metrics[metric_name] = {"metric": metric_name}
            metrics[metric_name][period] = q.get(key, 0) / 1e6

    return list(metrics.values())


def _format_fmp_cash_flow(cash_flow_data: List[Dict]) -> List[Dict]:
    """Format FMP cash flow data."""
    if not cash_flow_data:
        return []

    metrics = {}
    for q in cash_flow_data[:4]:
        period = q.get("date", "")[:7]
        if not period:
            continue

        for key, metric_name in [
            ("operatingCashFlow", "Operating Cash Flow"),
            ("capitalExpenditure", "Capital Expenditure"),
            ("freeCashFlow", "Free Cash Flow"),
        ]:
            if metric_name not in metrics:
                metrics[metric_name] = {"metric": metric_name}
            metrics[metric_name][period] = q.get(key, 0) / 1e6

    return list(metrics.values())


def get_api_usage() -> Dict[str, Any]:
    """Get current API usage stats."""
    return {
        "calls_today": _calls_today,
        "daily_limit": DAILY_LIMIT,
        "remaining": DAILY_LIMIT - _calls_today,
        "has_api_key": bool(FMP_API_KEY),
    }
