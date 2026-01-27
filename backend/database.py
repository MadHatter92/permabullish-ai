"""
Database module with PostgreSQL (production) and SQLite (development) support.
Automatically detects DATABASE_URL environment variable to choose backend.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from pydantic import BaseModel
from contextlib import contextmanager

from config import MONTHLY_REPORT_LIMIT, ANONYMOUS_REPORT_LIMIT

# Determine database type from environment
DATABASE_URL = os.getenv("DATABASE_URL", "")
USE_POSTGRES = DATABASE_URL.startswith("postgres")

if USE_POSTGRES:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    # Render uses postgres:// but psycopg2 needs postgresql://
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
else:
    import sqlite3
    # Local development: use SQLite
    DATA_DIR = Path(__file__).resolve().parent.parent / "data"
    DATA_DIR.mkdir(exist_ok=True)
    DB_PATH = DATA_DIR / "research.db"
    print(f"Using SQLite database at: {DB_PATH}")


# Pydantic Models
class UserCreate(BaseModel):
    email: str
    password: str
    full_name: str


class User(BaseModel):
    id: int
    email: str
    full_name: str
    created_at: str
    is_active: bool = True
    subscription_tier: str = "free"


class ReportSummary(BaseModel):
    id: int
    company_name: str
    ticker: str
    recommendation: str
    target_price: float
    current_price: float
    created_at: str


class ReportDetail(ReportSummary):
    report_html: str


class UsageStats(BaseModel):
    reports_used: int
    reports_limit: int
    reports_remaining: int
    reset_date: str


@contextmanager
def get_db_connection():
    """Get a database connection (context manager for proper cleanup)."""
    if USE_POSTGRES:
        conn = psycopg2.connect(DATABASE_URL)
        try:
            yield conn
        finally:
            conn.close()
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()


def get_cursor(conn):
    """Get a cursor appropriate for the database type."""
    if USE_POSTGRES:
        return conn.cursor(cursor_factory=RealDictCursor)
    return conn.cursor()


def placeholder(index: int = None) -> str:
    """Return the appropriate placeholder for the database type."""
    if USE_POSTGRES:
        return "%s"
    return "?"


def init_database():
    """Initialize database tables."""
    with get_db_connection() as conn:
        cursor = get_cursor(conn)

        if USE_POSTGRES:
            # PostgreSQL schema
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT,
                    full_name TEXT NOT NULL,
                    google_id TEXT UNIQUE,
                    auth_provider TEXT DEFAULT 'local',
                    avatar_url TEXT,
                    subscription_tier TEXT DEFAULT 'free',
                    stripe_customer_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reports (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    company_name TEXT NOT NULL,
                    ticker TEXT NOT NULL,
                    exchange TEXT DEFAULT 'NSE',
                    sector TEXT,
                    current_price REAL,
                    target_price REAL,
                    recommendation TEXT,
                    report_html TEXT NOT NULL,
                    report_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS usage (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    month_year TEXT NOT NULL,
                    reports_generated INTEGER DEFAULT 0,
                    UNIQUE(user_id, month_year)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS anonymous_usage (
                    id SERIAL PRIMARY KEY,
                    identifier TEXT UNIQUE NOT NULL,
                    reports_generated INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Usage limits table for feature gating (paywall preparation)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS usage_limits (
                    id SERIAL PRIMARY KEY,
                    tier TEXT UNIQUE NOT NULL,
                    monthly_reports INTEGER NOT NULL,
                    features JSONB DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Insert default tiers if not exists
            cursor.execute("""
                INSERT INTO usage_limits (tier, monthly_reports, features)
                VALUES
                    ('free', 20, '{"stock_research": true, "mf_analytics": false, "pms_tracker": false}'),
                    ('pro', 100, '{"stock_research": true, "mf_analytics": true, "pms_tracker": true}'),
                    ('enterprise', 1000, '{"stock_research": true, "mf_analytics": true, "pms_tracker": true, "api_access": true}')
                ON CONFLICT (tier) DO NOTHING
            """)

        else:
            # SQLite schema (for local development)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT,
                    full_name TEXT NOT NULL,
                    google_id TEXT UNIQUE,
                    auth_provider TEXT DEFAULT 'local',
                    avatar_url TEXT,
                    subscription_tier TEXT DEFAULT 'free',
                    stripe_customer_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    company_name TEXT NOT NULL,
                    ticker TEXT NOT NULL,
                    exchange TEXT DEFAULT 'NSE',
                    sector TEXT,
                    current_price REAL,
                    target_price REAL,
                    recommendation TEXT,
                    report_html TEXT NOT NULL,
                    report_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    month_year TEXT NOT NULL,
                    reports_generated INTEGER DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    UNIQUE(user_id, month_year)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS anonymous_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    identifier TEXT UNIQUE NOT NULL,
                    reports_generated INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS usage_limits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tier TEXT UNIQUE NOT NULL,
                    monthly_reports INTEGER NOT NULL,
                    features TEXT DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

        conn.commit()
        print(f"Database initialized successfully ({'PostgreSQL' if USE_POSTGRES else 'SQLite'}).")


def _dict_from_row(row) -> Optional[dict]:
    """Convert a database row to a dictionary."""
    if row is None:
        return None
    if USE_POSTGRES:
        return dict(row)
    return dict(row)


# User Operations
def create_user(email: str, password_hash: str, full_name: str) -> Optional[int]:
    """Create a new user and return user ID."""
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        try:
            if USE_POSTGRES:
                cursor.execute(
                    "INSERT INTO users (email, password_hash, full_name) VALUES (%s, %s, %s) RETURNING id",
                    (email, password_hash, full_name)
                )
                result = cursor.fetchone()
                conn.commit()
                return result['id'] if result else None
            else:
                cursor.execute(
                    "INSERT INTO users (email, password_hash, full_name) VALUES (?, ?, ?)",
                    (email, password_hash, full_name)
                )
                conn.commit()
                return cursor.lastrowid
        except Exception:
            return None


def get_user_by_email(email: str) -> Optional[dict]:
    """Get user by email."""
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        p = placeholder()
        cursor.execute(f"SELECT * FROM users WHERE email = {p}", (email,))
        row = cursor.fetchone()
        return _dict_from_row(row)


def get_user_by_id(user_id: int) -> Optional[dict]:
    """Get user by ID."""
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        p = placeholder()
        cursor.execute(f"SELECT * FROM users WHERE id = {p}", (user_id,))
        row = cursor.fetchone()
        return _dict_from_row(row)


def get_user_by_google_id(google_id: str) -> Optional[dict]:
    """Get user by Google ID."""
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        p = placeholder()
        cursor.execute(f"SELECT * FROM users WHERE google_id = {p}", (google_id,))
        row = cursor.fetchone()
        return _dict_from_row(row)


def get_or_create_google_user(google_id: str, email: str, full_name: str, avatar_url: str = None) -> dict:
    """Get existing Google user or create a new one."""
    # First, try to find by google_id
    user = get_user_by_google_id(google_id)
    if user:
        return user

    # Check if email exists (user might have registered with email/password before)
    user = get_user_by_email(email)
    if user:
        # Link Google account to existing user
        with get_db_connection() as conn:
            cursor = get_cursor(conn)
            p = placeholder()
            cursor.execute(
                f"UPDATE users SET google_id = {p}, auth_provider = 'google', avatar_url = {p} WHERE id = {p}",
                (google_id, avatar_url, user["id"])
            )
            conn.commit()
        user["google_id"] = google_id
        user["auth_provider"] = "google"
        user["avatar_url"] = avatar_url
        return user

    # Create new Google user
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        if USE_POSTGRES:
            cursor.execute(
                """INSERT INTO users (email, password_hash, full_name, google_id, auth_provider, avatar_url)
                   VALUES (%s, NULL, %s, %s, 'google', %s) RETURNING id""",
                (email, full_name, google_id, avatar_url)
            )
            result = cursor.fetchone()
            conn.commit()
            user_id = result['id']
        else:
            cursor.execute(
                """INSERT INTO users (email, password_hash, full_name, google_id, auth_provider, avatar_url)
                   VALUES (?, NULL, ?, ?, 'google', ?)""",
                (email, full_name, google_id, avatar_url)
            )
            conn.commit()
            user_id = cursor.lastrowid

    return {
        "id": user_id,
        "email": email,
        "full_name": full_name,
        "google_id": google_id,
        "auth_provider": "google",
        "avatar_url": avatar_url,
        "is_active": True,
        "subscription_tier": "free"
    }


# Report Operations
def save_report(
    user_id: int,
    company_name: str,
    ticker: str,
    exchange: str,
    sector: str,
    current_price: float,
    target_price: float,
    recommendation: str,
    report_html: str,
    report_data: str = None
) -> int:
    """Save a generated report and return report ID."""
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        if USE_POSTGRES:
            cursor.execute("""
                INSERT INTO reports
                (user_id, company_name, ticker, exchange, sector, current_price, target_price, recommendation, report_html, report_data)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
            """, (user_id, company_name, ticker, exchange, sector, current_price, target_price, recommendation, report_html, report_data))
            result = cursor.fetchone()
            conn.commit()
            return result['id']
        else:
            cursor.execute("""
                INSERT INTO reports
                (user_id, company_name, ticker, exchange, sector, current_price, target_price, recommendation, report_html, report_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, company_name, ticker, exchange, sector, current_price, target_price, recommendation, report_html, report_data))
            conn.commit()
            return cursor.lastrowid


def get_user_reports(user_id: int, limit: int = 50) -> List[dict]:
    """Get user's report history."""
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        p = placeholder()
        cursor.execute(f"""
            SELECT id, company_name, ticker, recommendation, target_price, current_price, created_at
            FROM reports
            WHERE user_id = {p}
            ORDER BY created_at DESC
            LIMIT {p}
        """, (user_id, limit))
        rows = cursor.fetchall()
        return [_dict_from_row(row) for row in rows]


def get_report_by_id(report_id: int, user_id: int) -> Optional[dict]:
    """Get a specific report by ID (ensuring user ownership)."""
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        p = placeholder()
        cursor.execute(f"""
            SELECT * FROM reports
            WHERE id = {p} AND user_id = {p}
        """, (report_id, user_id))
        row = cursor.fetchone()
        return _dict_from_row(row)


def delete_report(report_id: int, user_id: int) -> bool:
    """Delete a report (ensuring user ownership)."""
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        p = placeholder()
        cursor.execute(f"DELETE FROM reports WHERE id = {p} AND user_id = {p}", (report_id, user_id))
        conn.commit()
        return cursor.rowcount > 0


# Usage Operations
def get_current_month_year() -> str:
    """Get current month-year string."""
    return datetime.now().strftime("%Y-%m")


def get_usage(user_id: int) -> dict:
    """Get user's usage for current month."""
    month_year = get_current_month_year()
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        p = placeholder()
        cursor.execute(
            f"SELECT reports_generated FROM usage WHERE user_id = {p} AND month_year = {p}",
            (user_id, month_year)
        )
        row = cursor.fetchone()

    reports_used = row["reports_generated"] if row else 0

    # Calculate reset date (1st of next month)
    now = datetime.now()
    if now.month == 12:
        reset_date = datetime(now.year + 1, 1, 1)
    else:
        reset_date = datetime(now.year, now.month + 1, 1)

    return {
        "reports_used": reports_used,
        "reports_limit": MONTHLY_REPORT_LIMIT,
        "reports_remaining": max(0, MONTHLY_REPORT_LIMIT - reports_used),
        "reset_date": reset_date.strftime("%B %d, %Y")
    }


def increment_usage(user_id: int) -> bool:
    """Increment usage count for current month. Returns False if limit reached."""
    month_year = get_current_month_year()
    usage = get_usage(user_id)

    if usage["reports_remaining"] <= 0:
        return False

    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        if USE_POSTGRES:
            cursor.execute("""
                INSERT INTO usage (user_id, month_year, reports_generated)
                VALUES (%s, %s, 1)
                ON CONFLICT(user_id, month_year)
                DO UPDATE SET reports_generated = usage.reports_generated + 1
            """, (user_id, month_year))
        else:
            cursor.execute("""
                INSERT INTO usage (user_id, month_year, reports_generated)
                VALUES (?, ?, 1)
                ON CONFLICT(user_id, month_year)
                DO UPDATE SET reports_generated = reports_generated + 1
            """, (user_id, month_year))
        conn.commit()
    return True


def can_generate_report(user_id: int) -> bool:
    """Check if user can generate more reports this month."""
    usage = get_usage(user_id)
    return usage["reports_remaining"] > 0


# Anonymous Usage Operations
def get_anonymous_usage(identifier: str) -> dict:
    """Get anonymous user's usage stats."""
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        p = placeholder()
        cursor.execute(
            f"SELECT reports_generated FROM anonymous_usage WHERE identifier = {p}",
            (identifier,)
        )
        row = cursor.fetchone()

    reports_used = row["reports_generated"] if row else 0

    return {
        "reports_used": reports_used,
        "reports_limit": ANONYMOUS_REPORT_LIMIT,
        "reports_remaining": max(0, ANONYMOUS_REPORT_LIMIT - reports_used)
    }


def can_anonymous_generate(identifier: str) -> bool:
    """Check if anonymous user can generate more reports."""
    usage = get_anonymous_usage(identifier)
    return usage["reports_remaining"] > 0


def increment_anonymous_usage(identifier: str) -> bool:
    """Increment anonymous usage count. Returns False if limit reached."""
    if not can_anonymous_generate(identifier):
        return False

    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        if USE_POSTGRES:
            cursor.execute("""
                INSERT INTO anonymous_usage (identifier, reports_generated, last_used_at)
                VALUES (%s, 1, CURRENT_TIMESTAMP)
                ON CONFLICT(identifier)
                DO UPDATE SET reports_generated = anonymous_usage.reports_generated + 1, last_used_at = CURRENT_TIMESTAMP
            """, (identifier,))
        else:
            cursor.execute("""
                INSERT INTO anonymous_usage (identifier, reports_generated, last_used_at)
                VALUES (?, 1, CURRENT_TIMESTAMP)
                ON CONFLICT(identifier)
                DO UPDATE SET reports_generated = reports_generated + 1, last_used_at = CURRENT_TIMESTAMP
            """, (identifier,))
        conn.commit()
    return True


# ============================================
# MF Analytics Operations
# ============================================

def get_mf_category_stats() -> List[dict]:
    """Get fund counts per category and sub-category."""
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        cursor.execute("""
            SELECT
                category,
                sub_category,
                COUNT(*) as count
            FROM mutual_funds
            WHERE category IS NOT NULL
              AND category != 'uncategorized'
              AND category != 'fmp'
            GROUP BY category, sub_category
            ORDER BY category, count DESC
        """)
        rows = cursor.fetchall()
        return [_dict_from_row(row) for row in rows]


def get_mf_funds(
    category: str = None,
    sub_category: str = None,
    plan: str = 'direct',
    option: str = 'growth',
    limit: int = 100,
    offset: int = 0
) -> dict:
    """Get funds by category with filtering and pagination."""
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        p = placeholder()

        where_conditions = ["mf.category IS NOT NULL"]
        params = []

        if category:
            where_conditions.append(f"mf.category = {p}")
            params.append(category)

        if sub_category:
            where_conditions.append(f"mf.sub_category = {p}")
            params.append(sub_category)

        # Filter by plan type (escape % for psycopg2)
        if plan == 'direct':
            where_conditions.append("mf.scheme_name LIKE '%%Direct%%'")
        elif plan == 'regular':
            where_conditions.append("(mf.scheme_name LIKE '%%Regular%%' OR mf.scheme_name NOT LIKE '%%Direct%%')")

        # Filter by option type (escape % for psycopg2)
        if option == 'growth':
            where_conditions.append("mf.scheme_name LIKE '%%Growth%%'")
        elif option == 'dividend':
            where_conditions.append("(mf.scheme_name LIKE '%%IDCW%%' OR mf.scheme_name LIKE '%%Dividend%%')")

        # Exclude FMPs
        where_conditions.append("mf.category != 'fmp'")

        # Only show active funds (NAV within last 30 days)
        if USE_POSTGRES:
            where_conditions.append("cr.latest_nav_date >= CURRENT_DATE - INTERVAL '30 days'")
        else:
            where_conditions.append("cr.latest_nav_date >= date('now', '-30 days')")

        where_clause = " AND ".join(where_conditions)

        # Get funds with returns
        query = f"""
            SELECT
                mf.scheme_code,
                mf.scheme_name,
                mf.fund_house as amc,
                mf.category,
                mf.sub_category,
                cr.latest_nav as nav,
                cr.latest_nav_date as nav_date,
                cr.return_1m as returns_1m,
                cr.return_3m as returns_3m,
                cr.return_6m as returns_6m,
                cr.return_1y as returns_1y,
                cr.return_3y as returns_3y,
                cr.return_5y as returns_5y
            FROM mutual_funds mf
            INNER JOIN mf_calculated_returns cr ON mf.scheme_code = cr.scheme_code
            WHERE {where_clause}
            ORDER BY mf.scheme_name
            LIMIT {p} OFFSET {p}
        """
        params.extend([limit, offset])
        cursor.execute(query, tuple(params))
        funds = [_dict_from_row(row) for row in cursor.fetchall()]

        # Get total count
        count_query = f"""
            SELECT COUNT(*) as total
            FROM mutual_funds mf
            INNER JOIN mf_calculated_returns cr ON mf.scheme_code = cr.scheme_code
            WHERE {where_clause}
        """
        cursor.execute(count_query, tuple(params[:-2]))  # Exclude limit/offset
        count_row = cursor.fetchone()
        total = count_row['total'] if USE_POSTGRES else count_row[0]

        return {
            "funds": funds,
            "total": total,
            "limit": limit,
            "offset": offset
        }


def get_mf_fund_by_scheme_code(scheme_code: str) -> Optional[dict]:
    """Get a single fund by scheme code."""
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        p = placeholder()
        cursor.execute(f"""
            SELECT
                mf.*,
                cr.latest_nav as nav,
                cr.latest_nav_date as nav_date,
                cr.return_1m as returns_1m,
                cr.return_3m as returns_3m,
                cr.return_6m as returns_6m,
                cr.return_1y as returns_1y,
                cr.return_3y as returns_3y,
                cr.return_5y as returns_5y,
                cr.calculated_at
            FROM mutual_funds mf
            LEFT JOIN mf_calculated_returns cr ON mf.scheme_code = cr.scheme_code
            WHERE mf.scheme_code = {p}
        """, (scheme_code,))
        row = cursor.fetchone()
        return _dict_from_row(row)


def search_mf_funds(query: str, limit: int = 20) -> List[dict]:
    """Search for mutual funds by name."""
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        p = placeholder()

        if USE_POSTGRES:
            nav_date_filter = "cr.latest_nav_date >= CURRENT_DATE - INTERVAL '30 days'"
        else:
            nav_date_filter = "cr.latest_nav_date >= date('now', '-30 days')"

        cursor.execute(f"""
            SELECT
                mf.scheme_code,
                mf.scheme_name,
                mf.fund_house as amc,
                mf.category,
                mf.sub_category
            FROM mutual_funds mf
            INNER JOIN mf_calculated_returns cr ON mf.scheme_code = cr.scheme_code
            WHERE mf.scheme_name ILIKE {p}
              AND mf.category != 'fmp'
              AND mf.scheme_name LIKE '%%Direct%%'
              AND mf.scheme_name LIKE '%%Growth%%'
              AND {nav_date_filter}
            ORDER BY mf.scheme_name
            LIMIT {p}
        """, (f"%{query}%", limit))
        rows = cursor.fetchall()
        return [_dict_from_row(row) for row in rows]


# Initialize database on module import
init_database()
