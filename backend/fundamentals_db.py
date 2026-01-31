"""
Stock Fundamentals Database Operations
Handles caching and retrieval of fundamental stock data.
"""

import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def init_fundamentals_table(conn) -> None:
    """Initialize the stock_fundamentals table."""
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stock_fundamentals (
            id SERIAL PRIMARY KEY,
            symbol TEXT UNIQUE NOT NULL,
            company_name TEXT,
            sector TEXT,
            industry TEXT,

            -- Key Ratios
            market_cap REAL,
            current_price REAL,
            high_low TEXT,
            pe_ratio REAL,
            pb_ratio REAL,
            dividend_yield REAL,
            roe REAL,
            roce REAL,
            book_value REAL,
            face_value REAL,

            -- Detailed data as JSON
            quarterly_results JSONB,
            profit_loss JSONB,
            balance_sheet JSONB,
            cash_flow JSONB,
            shareholding JSONB,
            ratios JSONB,

            -- Pros/Cons
            pros TEXT[],
            cons TEXT[],

            -- Metadata
            source_url TEXT,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_fundamentals_symbol
        ON stock_fundamentals(symbol)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_fundamentals_sector
        ON stock_fundamentals(sector)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_fundamentals_updated
        ON stock_fundamentals(last_updated)
    """)
    conn.commit()
    logger.info("stock_fundamentals table initialized")


def save_fundamentals(conn, data: Dict[str, Any]) -> bool:
    """Save or update fundamentals for a stock."""
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO stock_fundamentals (
                symbol, company_name, sector, industry,
                market_cap, current_price, high_low,
                pe_ratio, pb_ratio, dividend_yield, roe, roce,
                book_value, face_value,
                quarterly_results, profit_loss, balance_sheet,
                cash_flow, shareholding, ratios,
                pros, cons, source_url, last_updated
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP
            )
            ON CONFLICT (symbol) DO UPDATE SET
                company_name = EXCLUDED.company_name,
                sector = EXCLUDED.sector,
                industry = EXCLUDED.industry,
                market_cap = EXCLUDED.market_cap,
                current_price = EXCLUDED.current_price,
                high_low = EXCLUDED.high_low,
                pe_ratio = EXCLUDED.pe_ratio,
                pb_ratio = EXCLUDED.pb_ratio,
                dividend_yield = EXCLUDED.dividend_yield,
                roe = EXCLUDED.roe,
                roce = EXCLUDED.roce,
                book_value = EXCLUDED.book_value,
                face_value = EXCLUDED.face_value,
                quarterly_results = EXCLUDED.quarterly_results,
                profit_loss = EXCLUDED.profit_loss,
                balance_sheet = EXCLUDED.balance_sheet,
                cash_flow = EXCLUDED.cash_flow,
                shareholding = EXCLUDED.shareholding,
                ratios = EXCLUDED.ratios,
                pros = EXCLUDED.pros,
                cons = EXCLUDED.cons,
                source_url = EXCLUDED.source_url,
                last_updated = CURRENT_TIMESTAMP
        """, (
            data.get('symbol'),
            data.get('company_name'),
            data.get('sector'),
            data.get('industry'),
            data.get('market_cap'),
            data.get('current_price'),
            data.get('high_low'),
            data.get('pe_ratio'),
            data.get('pb_ratio'),
            data.get('dividend_yield'),
            data.get('roe'),
            data.get('roce'),
            data.get('book_value'),
            data.get('face_value'),
            json.dumps(data.get('quarterly_results', [])),
            json.dumps(data.get('profit_loss', [])),
            json.dumps(data.get('balance_sheet', [])),
            json.dumps(data.get('cash_flow', [])),
            json.dumps(data.get('shareholding', [])),
            json.dumps(data.get('ratios', {})),
            data.get('pros', []),
            data.get('cons', []),
            data.get('source_url'),
        ))
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Failed to save fundamentals for {data.get('symbol')}: {e}")
        conn.rollback()
        return False


def get_fundamentals(conn, symbol: str) -> Optional[Dict[str, Any]]:
    """Get cached fundamentals for a stock."""
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                symbol, company_name, sector, industry,
                market_cap, current_price, high_low,
                pe_ratio, pb_ratio, dividend_yield, roe, roce,
                book_value, face_value,
                quarterly_results, profit_loss, balance_sheet,
                cash_flow, shareholding, ratios,
                pros, cons, source_url, last_updated
            FROM stock_fundamentals
            WHERE symbol = %s
        """, (symbol.upper(),))

        row = cursor.fetchone()
        if not row:
            return None

        return {
            'symbol': row[0],
            'company_name': row[1],
            'sector': row[2],
            'industry': row[3],
            'market_cap': row[4],
            'current_price': row[5],
            'high_low': row[6],
            'pe_ratio': row[7],
            'pb_ratio': row[8],
            'dividend_yield': row[9],
            'roe': row[10],
            'roce': row[11],
            'book_value': row[12],
            'face_value': row[13],
            'quarterly_results': row[14] or [],
            'profit_loss': row[15] or [],
            'balance_sheet': row[16] or [],
            'cash_flow': row[17] or [],
            'shareholding': row[18] or [],
            'ratios': row[19] or {},
            'pros': row[20] or [],
            'cons': row[21] or [],
            'source_url': row[22],
            'last_updated': row[23],
        }
    except Exception as e:
        logger.error(f"Failed to get fundamentals for {symbol}: {e}")
        return None


def get_stale_stocks(conn, days: int = 30) -> List[str]:
    """Get symbols that haven't been updated in N days."""
    try:
        cursor = conn.cursor()
        cutoff = datetime.now() - timedelta(days=days)
        cursor.execute("""
            SELECT symbol FROM stock_fundamentals
            WHERE last_updated < %s
            ORDER BY last_updated ASC
        """, (cutoff,))
        return [row[0] for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"Failed to get stale stocks: {e}")
        return []


def get_missing_stocks(conn, symbols: List[str]) -> List[str]:
    """Get symbols that don't have fundamentals cached."""
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT symbol FROM stock_fundamentals
        """)
        existing = {row[0] for row in cursor.fetchall()}
        return [s for s in symbols if s.upper() not in existing]
    except Exception as e:
        logger.error(f"Failed to get missing stocks: {e}")
        return symbols


def get_fundamentals_count(conn) -> int:
    """Get count of stocks with cached fundamentals."""
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM stock_fundamentals")
        return cursor.fetchone()[0]
    except Exception as e:
        logger.error(f"Failed to get fundamentals count: {e}")
        return 0


def is_fresh(conn, symbol: str, max_age_days: int = 30) -> bool:
    """Check if fundamentals for a symbol are fresh enough."""
    try:
        cursor = conn.cursor()
        cutoff = datetime.now() - timedelta(days=max_age_days)
        cursor.execute("""
            SELECT 1 FROM stock_fundamentals
            WHERE symbol = %s AND last_updated > %s
        """, (symbol.upper(), cutoff))
        return cursor.fetchone() is not None
    except Exception as e:
        logger.error(f"Failed to check freshness for {symbol}: {e}")
        return False
