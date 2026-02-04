"""
Database module with PostgreSQL (production) and SQLite (development) support.
Automatically detects DATABASE_URL environment variable to choose backend.
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from pydantic import BaseModel
from contextlib import contextmanager

from config import MONTHLY_REPORT_LIMIT, ANONYMOUS_REPORT_LIMIT, SUBSCRIPTION_TIERS

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


class CachedReport(BaseModel):
    id: int
    ticker: str
    exchange: str
    company_name: str
    sector: Optional[str]
    current_price: float
    ai_target_price: float
    recommendation: str
    report_html: str
    report_data: Optional[str]
    language: str = 'en'
    generated_at: str
    is_outdated: bool = False


class WatchlistItem(BaseModel):
    id: int
    ticker: str
    exchange: str
    company_name: Optional[str]
    added_at: str
    has_report: bool = False


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
                    subscription_expires_at TIMESTAMP,
                    payment_customer_id TEXT,  -- For Cashfree or future payment provider
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE,
                    -- Email tracking columns
                    last_activity_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    welcome_email_sent BOOLEAN DEFAULT FALSE,
                    last_reengagement_email_at TIMESTAMP,
                    reengagement_email_count INTEGER DEFAULT 0,
                    last_expiry_email_at TIMESTAMP,
                    expiry_email_count INTEGER DEFAULT 0
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
            # Note: free=5 (logged-in), basic=50/mo, pro=100/mo
            cursor.execute("""
                INSERT INTO usage_limits (tier, monthly_reports, features)
                VALUES
                    ('free', 5, '{"stock_research": true}'),
                    ('basic', 50, '{"stock_research": true}'),
                    ('pro', 100, '{"stock_research": true}'),
                    ('enterprise', 10000, '{"stock_research": true, "api_access": true}')
                ON CONFLICT (tier) DO NOTHING
            """)

            # Report cache - shared reports across all users
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS report_cache (
                    id SERIAL PRIMARY KEY,
                    ticker VARCHAR(20) NOT NULL,
                    exchange VARCHAR(10) NOT NULL,
                    company_name VARCHAR(255),
                    sector VARCHAR(255),
                    current_price REAL,
                    ai_target_price REAL,
                    recommendation VARCHAR(50),
                    report_html TEXT,
                    report_data JSONB,
                    input_tokens INTEGER DEFAULT 0,
                    output_tokens INTEGER DEFAULT 0,
                    total_tokens INTEGER DEFAULT 0,
                    language VARCHAR(10) DEFAULT 'en',
                    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(ticker, exchange, language)
                )
            """)

            # Migration: Add language column if it doesn't exist (for existing databases)
            cursor.execute("""
                DO $$
                BEGIN
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                                   WHERE table_name='report_cache' AND column_name='language') THEN
                        ALTER TABLE report_cache ADD COLUMN language VARCHAR(10) DEFAULT 'en';
                        -- Drop old constraint and add new one
                        ALTER TABLE report_cache DROP CONSTRAINT IF EXISTS report_cache_ticker_exchange_key;
                        ALTER TABLE report_cache ADD CONSTRAINT report_cache_ticker_exchange_language_key
                            UNIQUE(ticker, exchange, language);
                    END IF;
                END $$;
            """)

            # User reports - links users to cached reports with user-specific data
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_reports (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    report_cache_id INTEGER NOT NULL REFERENCES report_cache(id),
                    user_target_price REAL,
                    first_viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, report_cache_id)
                )
            """)

            # Watchlist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS watchlist (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    ticker VARCHAR(20) NOT NULL,
                    exchange VARCHAR(10) NOT NULL,
                    company_name VARCHAR(255),
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, ticker, exchange)
                )
            """)

            # Subscriptions - payment history
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    tier VARCHAR(50) NOT NULL,
                    period_months INTEGER NOT NULL,
                    amount_paid DECIMAL(10,2),
                    currency VARCHAR(3) DEFAULT 'INR',
                    payment_id VARCHAR(255),
                    starts_at TIMESTAMP NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Stock fundamentals cache (from Screener.in)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS stock_fundamentals (
                    id SERIAL PRIMARY KEY,
                    symbol TEXT UNIQUE NOT NULL,
                    company_name TEXT,
                    sector TEXT,
                    industry TEXT,
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
                    quarterly_results JSONB,
                    profit_loss JSONB,
                    balance_sheet JSONB,
                    cash_flow JSONB,
                    shareholding JSONB,
                    ratios JSONB,
                    pros TEXT[],
                    cons TEXT[],
                    source_url TEXT,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_fundamentals_symbol ON stock_fundamentals(symbol)
            """)

            # Comparison cache - stores comparison results
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS comparison_cache (
                    id SERIAL PRIMARY KEY,
                    ticker_a VARCHAR(20) NOT NULL,
                    exchange_a VARCHAR(10) NOT NULL,
                    ticker_b VARCHAR(20) NOT NULL,
                    exchange_b VARCHAR(10) NOT NULL,
                    language VARCHAR(10) DEFAULT 'en',
                    verdict VARCHAR(20),
                    verdict_stock VARCHAR(20),
                    conviction VARCHAR(20),
                    one_line_verdict TEXT,
                    comparison_data JSONB,
                    input_tokens INTEGER DEFAULT 0,
                    output_tokens INTEGER DEFAULT 0,
                    total_tokens INTEGER DEFAULT 0,
                    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(ticker_a, exchange_a, ticker_b, exchange_b, language)
                )
            """)

            # User comparisons - links users to cached comparisons
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_comparisons (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    comparison_cache_id INTEGER NOT NULL REFERENCES comparison_cache(id),
                    first_viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, comparison_cache_id)
                )
            """)

            # Add subscription_expires_at column if not exists (migration)
            try:
                cursor.execute("""
                    ALTER TABLE users ADD COLUMN IF NOT EXISTS subscription_expires_at TIMESTAMP
                """)
            except:
                pass  # Column already exists

            # Add email tracking columns (migration)
            for col_sql in [
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS last_activity_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS welcome_email_sent BOOLEAN DEFAULT FALSE",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS last_reengagement_email_at TIMESTAMP",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS reengagement_email_count INTEGER DEFAULT 0",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS last_expiry_email_at TIMESTAMP",
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS expiry_email_count INTEGER DEFAULT 0",
            ]:
                try:
                    cursor.execute(col_sql)
                except:
                    pass  # Column already exists

            # External contacts table (for imported email lists)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS external_contacts (
                    id SERIAL PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    first_name TEXT,
                    last_name TEXT,
                    source TEXT DEFAULT 'import',
                    is_active BOOLEAN DEFAULT TRUE,
                    unsubscribed BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_reengagement_email_at TIMESTAMP,
                    reengagement_email_count INTEGER DEFAULT 0
                )
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
                    subscription_expires_at TIMESTAMP,
                    payment_customer_id TEXT,  -- For Cashfree or future payment provider
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1,
                    -- Email tracking columns
                    last_activity_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    welcome_email_sent BOOLEAN DEFAULT 0,
                    last_reengagement_email_at TIMESTAMP,
                    reengagement_email_count INTEGER DEFAULT 0,
                    last_expiry_email_at TIMESTAMP,
                    expiry_email_count INTEGER DEFAULT 0
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

            # Report cache - shared reports across all users
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS report_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker TEXT NOT NULL,
                    exchange TEXT NOT NULL,
                    company_name TEXT,
                    sector TEXT,
                    current_price REAL,
                    ai_target_price REAL,
                    recommendation TEXT,
                    report_html TEXT,
                    report_data TEXT,
                    input_tokens INTEGER DEFAULT 0,
                    output_tokens INTEGER DEFAULT 0,
                    total_tokens INTEGER DEFAULT 0,
                    language TEXT DEFAULT 'en',
                    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(ticker, exchange, language)
                )
            """)

            # Migration: Add language column if it doesn't exist (for existing databases)
            try:
                cursor.execute("ALTER TABLE report_cache ADD COLUMN language TEXT DEFAULT 'en'")
            except:
                pass  # Column already exists

            # User reports - links users to cached reports with user-specific data
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    report_cache_id INTEGER NOT NULL,
                    user_target_price REAL,
                    first_viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    FOREIGN KEY (report_cache_id) REFERENCES report_cache(id),
                    UNIQUE(user_id, report_cache_id)
                )
            """)

            # Watchlist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS watchlist (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    ticker TEXT NOT NULL,
                    exchange TEXT NOT NULL,
                    company_name TEXT,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    UNIQUE(user_id, ticker, exchange)
                )
            """)

            # Subscriptions - payment history
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    tier TEXT NOT NULL,
                    period_months INTEGER NOT NULL,
                    amount_paid REAL,
                    currency TEXT DEFAULT 'INR',
                    payment_id TEXT,
                    starts_at TIMESTAMP NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)

            # Stock fundamentals cache (from Screener.in)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS stock_fundamentals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT UNIQUE NOT NULL,
                    company_name TEXT,
                    sector TEXT,
                    industry TEXT,
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
                    quarterly_results TEXT,
                    profit_loss TEXT,
                    balance_sheet TEXT,
                    cash_flow TEXT,
                    shareholding TEXT,
                    ratios TEXT,
                    pros TEXT,
                    cons TEXT,
                    source_url TEXT,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Comparison cache - stores comparison results
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS comparison_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker_a TEXT NOT NULL,
                    exchange_a TEXT NOT NULL,
                    ticker_b TEXT NOT NULL,
                    exchange_b TEXT NOT NULL,
                    language TEXT DEFAULT 'en',
                    verdict TEXT,
                    verdict_stock TEXT,
                    conviction TEXT,
                    one_line_verdict TEXT,
                    comparison_data TEXT,
                    input_tokens INTEGER DEFAULT 0,
                    output_tokens INTEGER DEFAULT 0,
                    total_tokens INTEGER DEFAULT 0,
                    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(ticker_a, exchange_a, ticker_b, exchange_b, language)
                )
            """)

            # User comparisons - links users to cached comparisons
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_comparisons (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    comparison_cache_id INTEGER NOT NULL,
                    first_viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    FOREIGN KEY (comparison_cache_id) REFERENCES comparison_cache(id),
                    UNIQUE(user_id, comparison_cache_id)
                )
            """)

            # SQLite migrations for email tracking columns
            for col_name, col_def in [
                ("last_activity_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
                ("welcome_email_sent", "BOOLEAN DEFAULT 0"),
                ("last_reengagement_email_at", "TIMESTAMP"),
                ("reengagement_email_count", "INTEGER DEFAULT 0"),
                ("last_expiry_email_at", "TIMESTAMP"),
                ("expiry_email_count", "INTEGER DEFAULT 0"),
            ]:
                try:
                    cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_def}")
                except:
                    pass  # Column already exists

            # External contacts table (SQLite)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS external_contacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    first_name TEXT,
                    last_name TEXT,
                    source TEXT DEFAULT 'import',
                    is_active INTEGER DEFAULT 1,
                    unsubscribed INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_reengagement_email_at TIMESTAMP,
                    reengagement_email_count INTEGER DEFAULT 0
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
    is_new_user = True
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

    # Send welcome email for new Google users
    if is_new_user:
        try:
            from email_service import send_welcome_email, get_featured_reports_for_email, get_first_name
            sample_reports = get_featured_reports_for_email()
            first_name = get_first_name(full_name)
            if send_welcome_email(email, first_name, sample_reports):
                mark_welcome_email_sent(user_id)
        except Exception as e:
            print(f"[DB] Failed to send welcome email to {email}: {e}")

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


def get_user_subscription_tier(user_id: int) -> str:
    """Get user's subscription tier."""
    user = get_user_by_id(user_id)
    return user.get("subscription_tier", "free") if user else "free"


def get_usage(user_id: int) -> dict:
    """Get user's usage based on their subscription tier."""
    user = get_user_by_id(user_id)
    tier = user.get("subscription_tier", "free") if user else "free"
    tier_config = SUBSCRIPTION_TIERS.get(tier, SUBSCRIPTION_TIERS["free"])

    is_lifetime = tier_config.get("is_lifetime", False)
    reports_limit = tier_config.get("reports_limit", 3)

    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        p = placeholder()

        if is_lifetime:
            # For free tier: count total reports ever generated
            cursor.execute(
                f"SELECT COALESCE(SUM(reports_generated), 0) as total FROM usage WHERE user_id = {p}",
                (user_id,)
            )
            row = cursor.fetchone()
            reports_used = row["total"] if row and row["total"] else 0
            reset_date = None
        else:
            # For paid tiers: count current month only
            month_year = get_current_month_year()
            cursor.execute(
                f"SELECT reports_generated FROM usage WHERE user_id = {p} AND month_year = {p}",
                (user_id, month_year)
            )
            row = cursor.fetchone()
            reports_used = row["reports_generated"] if row else 0

            # Calculate reset date (1st of next month)
            now = datetime.now()
            if now.month == 12:
                reset_date = datetime(now.year + 1, 1, 1).strftime("%B %d, %Y")
            else:
                reset_date = datetime(now.year, now.month + 1, 1).strftime("%B %d, %Y")

    return {
        "tier": tier,
        "tier_name": tier_config.get("name", tier.title()),
        "reports_used": reports_used,
        "reports_limit": reports_limit,
        "reports_remaining": max(0, reports_limit - reports_used),
        "is_lifetime": is_lifetime,
        "reset_date": reset_date
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


def reset_user_usage(user_id: int) -> bool:
    """Reset user's usage count for testing purposes."""
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        month_year = datetime.now().strftime("%Y-%m")
        p = placeholder()
        cursor.execute(
            f"UPDATE usage SET reports_generated = 0 WHERE user_id = {p} AND month_year = {p}",
            (user_id, month_year)
        )
        conn.commit()
        return True


# ============================================
# Subscription Operations
# ============================================

def update_user_subscription(user_id: int, tier: str, expires_at: datetime = None) -> bool:
    """Update user's subscription tier."""
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        p = placeholder()
        if expires_at:
            cursor.execute(
                f"UPDATE users SET subscription_tier = {p}, subscription_expires_at = {p} WHERE id = {p}",
                (tier, expires_at, user_id)
            )
        else:
            cursor.execute(
                f"UPDATE users SET subscription_tier = {p} WHERE id = {p}",
                (tier, user_id)
            )
        conn.commit()
        return cursor.rowcount > 0


def get_subscription_status(user_id: int) -> dict:
    """Get detailed subscription status for a user."""
    user = get_user_by_id(user_id)
    if not user:
        return None

    tier = user.get("subscription_tier", "free")
    tier_config = SUBSCRIPTION_TIERS.get(tier, SUBSCRIPTION_TIERS["free"])
    usage = get_usage(user_id)

    # Check if subscription has expired
    expires_at = user.get("subscription_expires_at")
    is_expired = False
    if expires_at and tier != "free":
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00').replace(' ', 'T'))
        is_expired = datetime.now() > expires_at.replace(tzinfo=None)

    return {
        "tier": tier,
        "tier_name": tier_config.get("name", tier.title()),
        "description": tier_config.get("description", ""),
        "reports_limit": tier_config.get("reports_limit", 3),
        "reports_used": usage["reports_used"],
        "reports_remaining": usage["reports_remaining"],
        "is_lifetime": tier_config.get("is_lifetime", False),
        "reset_date": usage.get("reset_date"),
        "expires_at": expires_at.isoformat() if expires_at else None,
        "is_expired": is_expired,
        "features": tier_config.get("features", {}),
        "can_generate": usage["reports_remaining"] > 0 and not is_expired
    }


def create_subscription_record(
    user_id: int,
    tier: str,
    period_months: int,
    amount_paid: float,
    payment_id: str = None
) -> Optional[int]:
    """Create a subscription record after successful payment."""
    from datetime import timedelta

    starts_at = datetime.now()
    expires_at = starts_at + timedelta(days=period_months * 30)

    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        if USE_POSTGRES:
            cursor.execute("""
                INSERT INTO subscriptions (user_id, tier, period_months, amount_paid, payment_id, starts_at, expires_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (user_id, tier, period_months, amount_paid, payment_id, starts_at, expires_at))
            result = cursor.fetchone()
            subscription_id = result['id'] if result else None
        else:
            cursor.execute("""
                INSERT INTO subscriptions (user_id, tier, period_months, amount_paid, payment_id, starts_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, tier, period_months, amount_paid, payment_id, starts_at, expires_at))
            subscription_id = cursor.lastrowid

        # Update user's subscription tier
        update_user_subscription(user_id, tier, expires_at)

        conn.commit()
        return subscription_id


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


# ============================================
# Report Cache Operations
# ============================================

REPORT_FRESHNESS_DAYS = 15


def get_cached_report(ticker: str, exchange: str, language: str = 'en') -> Optional[dict]:
    """Get a cached report by ticker, exchange, and language."""
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        p = placeholder()
        cursor.execute(f"""
            SELECT * FROM report_cache
            WHERE ticker = {p} AND exchange = {p} AND (language = {p} OR language IS NULL)
        """, (ticker.upper(), exchange.upper(), language))
        row = cursor.fetchone()
        if row:
            result = _dict_from_row(row)
            # Calculate if report is outdated
            if result.get('generated_at'):
                from datetime import datetime, timedelta
                generated = result['generated_at']
                if isinstance(generated, str):
                    generated = datetime.fromisoformat(generated.replace('Z', '+00:00').replace(' ', 'T'))
                result['is_outdated'] = (datetime.now() - generated.replace(tzinfo=None)) > timedelta(days=REPORT_FRESHNESS_DAYS)
            # Ensure language is returned
            result['language'] = result.get('language', 'en')
            return result
        return None


def save_cached_report(
    ticker: str,
    exchange: str,
    company_name: str,
    sector: str,
    current_price: float,
    ai_target_price: float,
    recommendation: str,
    report_html: str,
    report_data: str = None,
    input_tokens: int = 0,
    output_tokens: int = 0,
    total_tokens: int = 0,
    language: str = 'en'
) -> int:
    """Save or update a cached report. Returns the report cache ID."""
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        if USE_POSTGRES:
            cursor.execute("""
                INSERT INTO report_cache
                (ticker, exchange, company_name, sector, current_price, ai_target_price, recommendation, report_html, report_data, input_tokens, output_tokens, total_tokens, language, generated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (ticker, exchange, language)
                DO UPDATE SET
                    company_name = EXCLUDED.company_name,
                    sector = EXCLUDED.sector,
                    current_price = EXCLUDED.current_price,
                    ai_target_price = EXCLUDED.ai_target_price,
                    recommendation = EXCLUDED.recommendation,
                    report_html = EXCLUDED.report_html,
                    report_data = EXCLUDED.report_data,
                    input_tokens = EXCLUDED.input_tokens,
                    output_tokens = EXCLUDED.output_tokens,
                    total_tokens = EXCLUDED.total_tokens,
                    generated_at = CURRENT_TIMESTAMP
                RETURNING id
            """, (ticker.upper(), exchange.upper(), company_name, sector, current_price, ai_target_price, recommendation, report_html, report_data, input_tokens, output_tokens, total_tokens, language))
            result = cursor.fetchone()
            conn.commit()
            return result['id']
        else:
            # SQLite: try insert, if conflict, update and get id
            cursor.execute("""
                INSERT INTO report_cache
                (ticker, exchange, company_name, sector, current_price, ai_target_price, recommendation, report_html, report_data, input_tokens, output_tokens, total_tokens, language, generated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT (ticker, exchange, language)
                DO UPDATE SET
                    company_name = excluded.company_name,
                    sector = excluded.sector,
                    current_price = excluded.current_price,
                    ai_target_price = excluded.ai_target_price,
                    recommendation = excluded.recommendation,
                    report_html = excluded.report_html,
                    report_data = excluded.report_data,
                    input_tokens = excluded.input_tokens,
                    output_tokens = excluded.output_tokens,
                    total_tokens = excluded.total_tokens,
                    generated_at = CURRENT_TIMESTAMP
            """, (ticker.upper(), exchange.upper(), company_name, sector, current_price, ai_target_price, recommendation, report_html, report_data, input_tokens, output_tokens, total_tokens, language))
            conn.commit()
            # Get the id
            cursor.execute("SELECT id FROM report_cache WHERE ticker = ? AND exchange = ? AND language = ?", (ticker.upper(), exchange.upper(), language))
            row = cursor.fetchone()
            return row['id'] if row else cursor.lastrowid


# ============================================
# User Reports Operations
# ============================================

def link_user_to_report(user_id: int, report_cache_id: int, user_target_price: float = None) -> int:
    """Link a user to a cached report (tracks viewing). Returns user_report id."""
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        if USE_POSTGRES:
            cursor.execute("""
                INSERT INTO user_reports (user_id, report_cache_id, user_target_price, first_viewed_at, last_viewed_at)
                VALUES (%s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ON CONFLICT (user_id, report_cache_id)
                DO UPDATE SET last_viewed_at = CURRENT_TIMESTAMP
                RETURNING id
            """, (user_id, report_cache_id, user_target_price))
            result = cursor.fetchone()
            conn.commit()
            return result['id']
        else:
            cursor.execute("""
                INSERT INTO user_reports (user_id, report_cache_id, user_target_price, first_viewed_at, last_viewed_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ON CONFLICT (user_id, report_cache_id)
                DO UPDATE SET last_viewed_at = CURRENT_TIMESTAMP
            """, (user_id, report_cache_id, user_target_price))
            conn.commit()
            cursor.execute("SELECT id FROM user_reports WHERE user_id = ? AND report_cache_id = ?", (user_id, report_cache_id))
            row = cursor.fetchone()
            return row['id'] if row else cursor.lastrowid


def has_user_viewed_report(user_id: int, ticker: str, exchange: str) -> bool:
    """Check if user has previously viewed a report for this stock."""
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        p = placeholder()
        cursor.execute(f"""
            SELECT ur.id FROM user_reports ur
            JOIN report_cache rc ON ur.report_cache_id = rc.id
            WHERE ur.user_id = {p} AND rc.ticker = {p} AND rc.exchange = {p}
        """, (user_id, ticker.upper(), exchange.upper()))
        return cursor.fetchone() is not None


def get_user_report_history(user_id: int, limit: int = 50) -> List[dict]:
    """Get user's report history with freshness info."""
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        p = placeholder()
        cursor.execute(f"""
            SELECT
                rc.id as report_cache_id,
                rc.ticker,
                rc.exchange,
                rc.company_name,
                rc.sector,
                rc.current_price,
                rc.ai_target_price,
                rc.recommendation,
                rc.language,
                rc.generated_at,
                ur.user_target_price,
                ur.first_viewed_at,
                ur.last_viewed_at
            FROM user_reports ur
            JOIN report_cache rc ON ur.report_cache_id = rc.id
            WHERE ur.user_id = {p}
            ORDER BY ur.last_viewed_at DESC
            LIMIT {p}
        """, (user_id, limit))
        rows = cursor.fetchall()
        results = []
        for row in rows:
            item = _dict_from_row(row)
            # Ensure language has a default
            item['language'] = item.get('language', 'en')
            # Calculate freshness
            if item.get('generated_at'):
                from datetime import datetime, timedelta
                generated = item['generated_at']
                if isinstance(generated, str):
                    generated = datetime.fromisoformat(generated.replace('Z', '+00:00').replace(' ', 'T'))
                item['is_outdated'] = (datetime.now() - generated.replace(tzinfo=None)) > timedelta(days=REPORT_FRESHNESS_DAYS)
                item['days_old'] = (datetime.now() - generated.replace(tzinfo=None)).days
            results.append(item)
        return results


def get_user_target_price(user_id: int, report_cache_id: int) -> Optional[float]:
    """Get user's target price for a specific report."""
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        p = placeholder()
        cursor.execute(f"""
            SELECT user_target_price FROM user_reports
            WHERE user_id = {p} AND report_cache_id = {p}
        """, (user_id, report_cache_id))
        row = cursor.fetchone()
        if row:
            # Handle both dict (PostgreSQL) and tuple (SQLite) results
            price = row.get('user_target_price') if hasattr(row, 'get') else row[0]
            if price:
                return float(price)
        return None


def update_user_target_price(user_id: int, report_cache_id: int, target_price: float) -> bool:
    """Update user's target price for a stock."""
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        p = placeholder()
        cursor.execute(f"""
            UPDATE user_reports
            SET user_target_price = {p}
            WHERE user_id = {p} AND report_cache_id = {p}
        """, (target_price, user_id, report_cache_id))
        conn.commit()
        return cursor.rowcount > 0


def get_cached_report_by_id(report_cache_id: int) -> Optional[dict]:
    """Get a cached report by its ID."""
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        p = placeholder()
        cursor.execute(f"SELECT * FROM report_cache WHERE id = {p}", (report_cache_id,))
        row = cursor.fetchone()
        if row:
            result = _dict_from_row(row)
            if result.get('generated_at'):
                from datetime import datetime, timedelta
                generated = result['generated_at']
                if isinstance(generated, str):
                    generated = datetime.fromisoformat(generated.replace('Z', '+00:00').replace(' ', 'T'))
                result['is_outdated'] = (datetime.now() - generated.replace(tzinfo=None)) > timedelta(days=REPORT_FRESHNESS_DAYS)
            # Ensure language is returned
            result['language'] = result.get('language', 'en')
            return result
        return None


# ============================================
# Watchlist Operations
# ============================================

def add_to_watchlist(user_id: int, ticker: str, exchange: str, company_name: str = None) -> Optional[int]:
    """Add a stock to user's watchlist. Returns watchlist item id or None if already exists."""
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        try:
            if USE_POSTGRES:
                cursor.execute("""
                    INSERT INTO watchlist (user_id, ticker, exchange, company_name)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (user_id, ticker, exchange) DO NOTHING
                    RETURNING id
                """, (user_id, ticker.upper(), exchange.upper(), company_name))
                result = cursor.fetchone()
                conn.commit()
                return result['id'] if result else None
            else:
                cursor.execute("""
                    INSERT OR IGNORE INTO watchlist (user_id, ticker, exchange, company_name)
                    VALUES (?, ?, ?, ?)
                """, (user_id, ticker.upper(), exchange.upper(), company_name))
                conn.commit()
                if cursor.rowcount > 0:
                    return cursor.lastrowid
                return None
        except Exception:
            return None


def remove_from_watchlist(user_id: int, ticker: str, exchange: str) -> bool:
    """Remove a stock from user's watchlist."""
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        p = placeholder()
        cursor.execute(f"""
            DELETE FROM watchlist
            WHERE user_id = {p} AND ticker = {p} AND exchange = {p}
        """, (user_id, ticker.upper(), exchange.upper()))
        conn.commit()
        return cursor.rowcount > 0


def get_watchlist(user_id: int) -> List[dict]:
    """Get user's watchlist with report availability status."""
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        p = placeholder()
        cursor.execute(f"""
            SELECT
                w.id,
                w.ticker,
                w.exchange,
                w.company_name,
                w.added_at,
                rc.id as report_cache_id,
                rc.ai_target_price,
                rc.current_price as cached_price,
                rc.recommendation,
                rc.generated_at
            FROM watchlist w
            LEFT JOIN report_cache rc ON w.ticker = rc.ticker AND w.exchange = rc.exchange
            WHERE w.user_id = {p}
            ORDER BY w.added_at DESC
        """, (user_id,))
        rows = cursor.fetchall()
        results = []
        for row in rows:
            item = _dict_from_row(row)
            item['has_report'] = item.get('report_cache_id') is not None
            if item.get('generated_at'):
                from datetime import datetime, timedelta
                generated = item['generated_at']
                if isinstance(generated, str):
                    generated = datetime.fromisoformat(generated.replace('Z', '+00:00').replace(' ', 'T'))
                item['is_outdated'] = (datetime.now() - generated.replace(tzinfo=None)) > timedelta(days=REPORT_FRESHNESS_DAYS)
            results.append(item)
        return results


def is_in_watchlist(user_id: int, ticker: str, exchange: str) -> bool:
    """Check if a stock is in user's watchlist."""
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        p = placeholder()
        cursor.execute(f"""
            SELECT id FROM watchlist
            WHERE user_id = {p} AND ticker = {p} AND exchange = {p}
        """, (user_id, ticker.upper(), exchange.upper()))
        return cursor.fetchone() is not None


# ============================================
# Email Tracking Operations
# ============================================

def update_user_activity(user_id: int) -> bool:
    """Update user's last activity timestamp."""
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        p = placeholder()
        if USE_POSTGRES:
            cursor.execute(
                f"UPDATE users SET last_activity_at = CURRENT_TIMESTAMP WHERE id = {p}",
                (user_id,)
            )
        else:
            cursor.execute(
                f"UPDATE users SET last_activity_at = CURRENT_TIMESTAMP WHERE id = {p}",
                (user_id,)
            )
        conn.commit()
        return cursor.rowcount > 0


def mark_welcome_email_sent(user_id: int) -> bool:
    """Mark that welcome email has been sent to user."""
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        p = placeholder()
        if USE_POSTGRES:
            cursor.execute(
                f"UPDATE users SET welcome_email_sent = TRUE WHERE id = {p}",
                (user_id,)
            )
        else:
            cursor.execute(
                f"UPDATE users SET welcome_email_sent = 1 WHERE id = {p}",
                (user_id,)
            )
        conn.commit()
        return cursor.rowcount > 0


def update_reengagement_email_sent(user_id: int) -> bool:
    """Update user's re-engagement email tracking after sending an email."""
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        p = placeholder()
        if USE_POSTGRES:
            cursor.execute(
                f"""UPDATE users SET
                    last_reengagement_email_at = CURRENT_TIMESTAMP,
                    reengagement_email_count = COALESCE(reengagement_email_count, 0) + 1
                WHERE id = {p}""",
                (user_id,)
            )
        else:
            cursor.execute(
                f"""UPDATE users SET
                    last_reengagement_email_at = CURRENT_TIMESTAMP,
                    reengagement_email_count = COALESCE(reengagement_email_count, 0) + 1
                WHERE id = {p}""",
                (user_id,)
            )
        conn.commit()
        return cursor.rowcount > 0


def get_users_for_reengagement() -> List[dict]:
    """
    Get users who should receive re-engagement emails.

    Criteria:
    - Free tier (not paid)
    - Signed up within 6 months (180 days)
    - Inactive for 7+ days
    - Email timing:
      - Days 1-14 of signup: daily (if no email today)
      - Days 15-180: weekly (if no email in 7 days)
    """
    with get_db_connection() as conn:
        cursor = get_cursor(conn)

        if USE_POSTGRES:
            cursor.execute("""
                SELECT
                    id, email, full_name, created_at,
                    last_activity_at, last_reengagement_email_at,
                    reengagement_email_count, subscription_tier
                FROM users
                WHERE is_active = TRUE
                  AND subscription_tier = 'free'
                  AND created_at >= CURRENT_DATE - INTERVAL '180 days'
                  AND (last_activity_at IS NULL OR last_activity_at < CURRENT_DATE - INTERVAL '7 days')
                  AND (
                      -- Daily phase (first 14 days): send if no email today
                      (created_at >= CURRENT_DATE - INTERVAL '14 days'
                       AND (last_reengagement_email_at IS NULL
                            OR last_reengagement_email_at < CURRENT_DATE))
                      OR
                      -- Weekly phase (days 15-180): send if no email in 7 days
                      (created_at < CURRENT_DATE - INTERVAL '14 days'
                       AND (last_reengagement_email_at IS NULL
                            OR last_reengagement_email_at < CURRENT_DATE - INTERVAL '7 days'))
                  )
                ORDER BY created_at DESC
            """)
        else:
            cursor.execute("""
                SELECT
                    id, email, full_name, created_at,
                    last_activity_at, last_reengagement_email_at,
                    reengagement_email_count, subscription_tier
                FROM users
                WHERE is_active = 1
                  AND subscription_tier = 'free'
                  AND created_at >= date('now', '-180 days')
                  AND (last_activity_at IS NULL OR last_activity_at < date('now', '-7 days'))
                  AND (
                      -- Daily phase (first 14 days): send if no email today
                      (created_at >= date('now', '-14 days')
                       AND (last_reengagement_email_at IS NULL
                            OR last_reengagement_email_at < date('now')))
                      OR
                      -- Weekly phase (days 15-180): send if no email in 7 days
                      (created_at < date('now', '-14 days')
                       AND (last_reengagement_email_at IS NULL
                            OR last_reengagement_email_at < date('now', '-7 days')))
                  )
                ORDER BY created_at DESC
            """)

        rows = cursor.fetchall()
        return [_dict_from_row(row) for row in rows]


def get_external_contacts_for_reengagement() -> List[dict]:
    """
    Get external contacts who should receive re-engagement emails.

    Criteria:
    - Active and not unsubscribed
    - No email sent today
    """
    with get_db_connection() as conn:
        cursor = get_cursor(conn)

        if USE_POSTGRES:
            cursor.execute("""
                SELECT
                    id, email, first_name, last_name, source,
                    created_at, last_reengagement_email_at,
                    reengagement_email_count
                FROM external_contacts
                WHERE is_active = TRUE
                  AND unsubscribed = FALSE
                  AND (last_reengagement_email_at IS NULL
                       OR last_reengagement_email_at < CURRENT_DATE)
                ORDER BY created_at DESC
            """)
        else:
            cursor.execute("""
                SELECT
                    id, email, first_name, last_name, source,
                    created_at, last_reengagement_email_at,
                    reengagement_email_count
                FROM external_contacts
                WHERE is_active = 1
                  AND unsubscribed = 0
                  AND (last_reengagement_email_at IS NULL
                       OR last_reengagement_email_at < date('now'))
                ORDER BY created_at DESC
            """)

        rows = cursor.fetchall()
        return [_dict_from_row(row) for row in rows]


def update_external_contact_email_sent(contact_id: int) -> bool:
    """Update external contact's email tracking after sending an email."""
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        p = placeholder()
        cursor.execute(
            f"""UPDATE external_contacts SET
                last_reengagement_email_at = CURRENT_TIMESTAMP,
                reengagement_email_count = COALESCE(reengagement_email_count, 0) + 1
            WHERE id = {p}""",
            (contact_id,)
        )
        conn.commit()
        return cursor.rowcount > 0


def add_external_contact(email: str, first_name: str = None, last_name: str = None, source: str = 'import') -> Optional[int]:
    """Add an external contact. Returns contact ID or None if already exists."""
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        try:
            if USE_POSTGRES:
                cursor.execute(
                    """INSERT INTO external_contacts (email, first_name, last_name, source)
                       VALUES (%s, %s, %s, %s)
                       ON CONFLICT (email) DO UPDATE SET
                           first_name = COALESCE(EXCLUDED.first_name, external_contacts.first_name),
                           last_name = COALESCE(EXCLUDED.last_name, external_contacts.last_name)
                       RETURNING id""",
                    (email.lower().strip(), first_name, last_name, source)
                )
                result = cursor.fetchone()
                conn.commit()
                return result['id'] if result else None
            else:
                cursor.execute(
                    """INSERT OR REPLACE INTO external_contacts (email, first_name, last_name, source)
                       VALUES (?, ?, ?, ?)""",
                    (email.lower().strip(), first_name, last_name, source)
                )
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            print(f"Error adding external contact {email}: {e}")
            return None


def get_external_contact_count() -> int:
    """Get total count of active external contacts."""
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        if USE_POSTGRES:
            cursor.execute("SELECT COUNT(*) as count FROM external_contacts WHERE is_active = TRUE AND unsubscribed = FALSE")
        else:
            cursor.execute("SELECT COUNT(*) as count FROM external_contacts WHERE is_active = 1 AND unsubscribed = 0")
        result = cursor.fetchone()
        return result['count'] if result else 0


def get_users_with_expired_subscriptions() -> List[dict]:
    """
    Get users with expired paid subscriptions who need reminder emails.

    Criteria:
    - Had a paid subscription (basic, pro, enterprise)
    - Subscription has expired
    - Haven't been sent an expiry email recently (based on schedule)

    Schedule:
    - Day 0 (expiry day): Send reminder
    - Day 3: Send follow-up
    - Day 7: Send follow-up
    - Day 14+: Weekly reminders for up to 60 days
    """
    with get_db_connection() as conn:
        cursor = get_cursor(conn)

        if USE_POSTGRES:
            cursor.execute("""
                SELECT
                    u.id, u.email, u.full_name, u.created_at,
                    u.subscription_tier, u.subscription_expires_at,
                    u.last_expiry_email_at, u.expiry_email_count,
                    COALESCE(s.reports_used, 0) as reports_generated
                FROM users u
                LEFT JOIN (
                    SELECT user_id, COUNT(*) as reports_used
                    FROM user_reports
                    GROUP BY user_id
                ) s ON s.user_id = u.id
                WHERE u.is_active = TRUE
                  AND u.subscription_tier IN ('basic', 'pro', 'enterprise')
                  AND u.subscription_expires_at < CURRENT_TIMESTAMP
                  AND u.subscription_expires_at > CURRENT_TIMESTAMP - INTERVAL '60 days'
                  AND (
                      -- No email sent yet for this expiry
                      u.last_expiry_email_at IS NULL
                      OR u.last_expiry_email_at < u.subscription_expires_at
                      OR (
                          -- Day 0-3: daily
                          u.subscription_expires_at > CURRENT_TIMESTAMP - INTERVAL '3 days'
                          AND u.last_expiry_email_at < CURRENT_DATE
                      )
                      OR (
                          -- Day 3-7: every 3 days
                          u.subscription_expires_at BETWEEN CURRENT_TIMESTAMP - INTERVAL '7 days'
                                                        AND CURRENT_TIMESTAMP - INTERVAL '3 days'
                          AND u.last_expiry_email_at < CURRENT_DATE - INTERVAL '3 days'
                      )
                      OR (
                          -- Day 7+: weekly
                          u.subscription_expires_at < CURRENT_TIMESTAMP - INTERVAL '7 days'
                          AND u.last_expiry_email_at < CURRENT_DATE - INTERVAL '7 days'
                      )
                  )
                ORDER BY u.subscription_expires_at DESC
            """)
        else:
            cursor.execute("""
                SELECT
                    u.id, u.email, u.full_name, u.created_at,
                    u.subscription_tier, u.subscription_expires_at,
                    u.last_expiry_email_at, u.expiry_email_count,
                    COALESCE(s.reports_used, 0) as reports_generated
                FROM users u
                LEFT JOIN (
                    SELECT user_id, COUNT(*) as reports_used
                    FROM user_reports
                    GROUP BY user_id
                ) s ON s.user_id = u.id
                WHERE u.is_active = 1
                  AND u.subscription_tier IN ('basic', 'pro', 'enterprise')
                  AND u.subscription_expires_at < datetime('now')
                  AND u.subscription_expires_at > datetime('now', '-60 days')
                  AND (
                      u.last_expiry_email_at IS NULL
                      OR u.last_expiry_email_at < u.subscription_expires_at
                      OR (
                          u.subscription_expires_at > datetime('now', '-3 days')
                          AND u.last_expiry_email_at < date('now')
                      )
                      OR (
                          u.subscription_expires_at BETWEEN datetime('now', '-7 days')
                                                        AND datetime('now', '-3 days')
                          AND u.last_expiry_email_at < date('now', '-3 days')
                      )
                      OR (
                          u.subscription_expires_at < datetime('now', '-7 days')
                          AND u.last_expiry_email_at < date('now', '-7 days')
                      )
                  )
                ORDER BY u.subscription_expires_at DESC
            """)

        rows = cursor.fetchall()
        return [_dict_from_row(row) for row in rows]


def update_expiry_email_sent(user_id: int) -> bool:
    """Update user's expiry email tracking after sending an email."""
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        p = placeholder()
        cursor.execute(
            f"""UPDATE users SET
                last_expiry_email_at = CURRENT_TIMESTAMP,
                expiry_email_count = COALESCE(expiry_email_count, 0) + 1
            WHERE id = {p}""",
            (user_id,)
        )
        conn.commit()
        return cursor.rowcount > 0


def get_featured_reports(tickers: List[str]) -> List[dict]:
    """Get cached reports for featured tickers."""
    if not tickers:
        return []

    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        p = placeholder()

        # Build placeholders for IN clause
        placeholders = ", ".join([p] * len(tickers))
        upper_tickers = [t.upper() for t in tickers]

        cursor.execute(f"""
            SELECT
                id, ticker, exchange, company_name, sector,
                current_price, ai_target_price, recommendation, generated_at
            FROM report_cache
            WHERE ticker IN ({placeholders})
            ORDER BY generated_at DESC
        """, tuple(upper_tickers))

        rows = cursor.fetchall()
        return [_dict_from_row(row) for row in rows]


# ============================================
# Stock Fundamentals Operations
# ============================================

def get_cached_fundamentals(symbol: str) -> Optional[dict]:
    """
    Get cached fundamentals for a stock from Screener data.
    Returns None if not found or data is stale (>45 days old).
    """
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        p = placeholder()

        if USE_POSTGRES:
            cursor.execute(f"""
                SELECT
                    symbol, company_name, sector, industry,
                    market_cap, current_price, high_low,
                    pe_ratio, pb_ratio, dividend_yield, roe, roce,
                    book_value, face_value,
                    quarterly_results, profit_loss, balance_sheet,
                    cash_flow, shareholding, ratios,
                    pros, cons, source_url, last_updated
                FROM stock_fundamentals
                WHERE symbol = {p}
                  AND last_updated > CURRENT_TIMESTAMP - INTERVAL '45 days'
            """, (symbol.upper(),))
        else:
            cursor.execute(f"""
                SELECT
                    symbol, company_name, sector, industry,
                    market_cap, current_price, high_low,
                    pe_ratio, pb_ratio, dividend_yield, roe, roce,
                    book_value, face_value,
                    quarterly_results, profit_loss, balance_sheet,
                    cash_flow, shareholding, ratios,
                    pros, cons, source_url, last_updated
                FROM stock_fundamentals
                WHERE symbol = {p}
                  AND last_updated > datetime('now', '-45 days')
            """, (symbol.upper(),))

        row = cursor.fetchone()
        if not row:
            return None

        result = _dict_from_row(row)

        # Parse JSON fields if they're strings (SQLite)
        if not USE_POSTGRES:
            for field in ['quarterly_results', 'profit_loss', 'balance_sheet',
                         'cash_flow', 'shareholding', 'ratios', 'pros', 'cons']:
                if result.get(field) and isinstance(result[field], str):
                    try:
                        result[field] = json.loads(result[field])
                    except:
                        pass

        return result


def is_fundamentals_fresh(symbol: str, max_age_days: int = 45) -> bool:
    """Check if we have fresh fundamentals data for a symbol."""
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        p = placeholder()

        if USE_POSTGRES:
            cursor.execute(f"""
                SELECT 1 FROM stock_fundamentals
                WHERE symbol = {p}
                  AND last_updated > CURRENT_TIMESTAMP - INTERVAL '{max_age_days} days'
            """, (symbol.upper(),))
        else:
            cursor.execute(f"""
                SELECT 1 FROM stock_fundamentals
                WHERE symbol = {p}
                  AND last_updated > datetime('now', '-{max_age_days} days')
            """, (symbol.upper(),))

        return cursor.fetchone() is not None


# ============================================
# Comparison Cache Operations
# ============================================

def get_cached_comparison(
    ticker_a: str, exchange_a: str,
    ticker_b: str, exchange_b: str,
    language: str = 'en'
) -> Optional[dict]:
    """Get a cached comparison if it exists and is fresh (less than 7 days old)."""
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        p = placeholder()

        if USE_POSTGRES:
            cursor.execute(f"""
                SELECT * FROM comparison_cache
                WHERE ticker_a = {p} AND exchange_a = {p}
                  AND ticker_b = {p} AND exchange_b = {p}
                  AND language = {p}
                  AND generated_at > CURRENT_TIMESTAMP - INTERVAL '7 days'
            """, (ticker_a.upper(), exchange_a.upper(), ticker_b.upper(), exchange_b.upper(), language))
        else:
            cursor.execute(f"""
                SELECT * FROM comparison_cache
                WHERE ticker_a = {p} AND exchange_a = {p}
                  AND ticker_b = {p} AND exchange_b = {p}
                  AND language = {p}
                  AND generated_at > datetime('now', '-7 days')
            """, (ticker_a.upper(), exchange_a.upper(), ticker_b.upper(), exchange_b.upper(), language))

        row = cursor.fetchone()
        if row:
            result = _dict_from_row(row)
            # Parse comparison_data if it's a string (SQLite)
            if result.get('comparison_data') and isinstance(result['comparison_data'], str):
                try:
                    result['comparison_data'] = json.loads(result['comparison_data'])
                except:
                    pass
            return result
        return None


def save_comparison(
    ticker_a: str, exchange_a: str,
    ticker_b: str, exchange_b: str,
    verdict: str,
    verdict_stock: str,
    conviction: str,
    one_line_verdict: str,
    comparison_data: dict,
    input_tokens: int = 0,
    output_tokens: int = 0,
    total_tokens: int = 0,
    language: str = 'en'
) -> int:
    """Save or update a cached comparison. Returns the comparison cache ID."""
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        comparison_json = json.dumps(comparison_data) if comparison_data else None

        if USE_POSTGRES:
            cursor.execute("""
                INSERT INTO comparison_cache
                (ticker_a, exchange_a, ticker_b, exchange_b, language, verdict, verdict_stock, conviction, one_line_verdict, comparison_data, input_tokens, output_tokens, total_tokens, generated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (ticker_a, exchange_a, ticker_b, exchange_b, language)
                DO UPDATE SET
                    verdict = EXCLUDED.verdict,
                    verdict_stock = EXCLUDED.verdict_stock,
                    conviction = EXCLUDED.conviction,
                    one_line_verdict = EXCLUDED.one_line_verdict,
                    comparison_data = EXCLUDED.comparison_data,
                    input_tokens = EXCLUDED.input_tokens,
                    output_tokens = EXCLUDED.output_tokens,
                    total_tokens = EXCLUDED.total_tokens,
                    generated_at = CURRENT_TIMESTAMP
                RETURNING id
            """, (ticker_a.upper(), exchange_a.upper(), ticker_b.upper(), exchange_b.upper(), language,
                  verdict, verdict_stock, conviction, one_line_verdict, comparison_json,
                  input_tokens, output_tokens, total_tokens))
            result = cursor.fetchone()
            conn.commit()
            return result['id']
        else:
            cursor.execute("""
                INSERT INTO comparison_cache
                (ticker_a, exchange_a, ticker_b, exchange_b, language, verdict, verdict_stock, conviction, one_line_verdict, comparison_data, input_tokens, output_tokens, total_tokens, generated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT (ticker_a, exchange_a, ticker_b, exchange_b, language)
                DO UPDATE SET
                    verdict = excluded.verdict,
                    verdict_stock = excluded.verdict_stock,
                    conviction = excluded.conviction,
                    one_line_verdict = excluded.one_line_verdict,
                    comparison_data = excluded.comparison_data,
                    input_tokens = excluded.input_tokens,
                    output_tokens = excluded.output_tokens,
                    total_tokens = excluded.total_tokens,
                    generated_at = CURRENT_TIMESTAMP
            """, (ticker_a.upper(), exchange_a.upper(), ticker_b.upper(), exchange_b.upper(), language,
                  verdict, verdict_stock, conviction, one_line_verdict, comparison_json,
                  input_tokens, output_tokens, total_tokens))
            conn.commit()
            cursor.execute("""
                SELECT id FROM comparison_cache
                WHERE ticker_a = ? AND exchange_a = ? AND ticker_b = ? AND exchange_b = ? AND language = ?
            """, (ticker_a.upper(), exchange_a.upper(), ticker_b.upper(), exchange_b.upper(), language))
            row = cursor.fetchone()
            return row['id'] if row else cursor.lastrowid


def get_comparison_by_id(comparison_id: int) -> Optional[dict]:
    """Get a comparison by its ID."""
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        p = placeholder()
        cursor.execute(f"SELECT * FROM comparison_cache WHERE id = {p}", (comparison_id,))
        row = cursor.fetchone()
        if row:
            result = _dict_from_row(row)
            if result.get('comparison_data') and isinstance(result['comparison_data'], str):
                try:
                    result['comparison_data'] = json.loads(result['comparison_data'])
                except:
                    pass
            return result
        return None


def link_user_to_comparison(user_id: int, comparison_cache_id: int) -> int:
    """Link a user to a cached comparison (tracks viewing). Returns user_comparison id."""
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        if USE_POSTGRES:
            cursor.execute("""
                INSERT INTO user_comparisons (user_id, comparison_cache_id, first_viewed_at, last_viewed_at)
                VALUES (%s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ON CONFLICT (user_id, comparison_cache_id)
                DO UPDATE SET last_viewed_at = CURRENT_TIMESTAMP
                RETURNING id
            """, (user_id, comparison_cache_id))
            result = cursor.fetchone()
            conn.commit()
            return result['id']
        else:
            cursor.execute("""
                INSERT INTO user_comparisons (user_id, comparison_cache_id, first_viewed_at, last_viewed_at)
                VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ON CONFLICT (user_id, comparison_cache_id)
                DO UPDATE SET last_viewed_at = CURRENT_TIMESTAMP
            """, (user_id, comparison_cache_id))
            conn.commit()
            cursor.execute("SELECT id FROM user_comparisons WHERE user_id = ? AND comparison_cache_id = ?",
                          (user_id, comparison_cache_id))
            row = cursor.fetchone()
            return row['id'] if row else cursor.lastrowid


def get_user_comparison_history(user_id: int, limit: int = 50) -> List[dict]:
    """Get user's comparison history."""
    with get_db_connection() as conn:
        cursor = get_cursor(conn)
        p = placeholder()
        cursor.execute(f"""
            SELECT
                cc.id as comparison_cache_id,
                cc.ticker_a,
                cc.exchange_a,
                cc.ticker_b,
                cc.exchange_b,
                cc.verdict,
                cc.verdict_stock,
                cc.conviction,
                cc.one_line_verdict,
                cc.language,
                cc.generated_at,
                uc.first_viewed_at,
                uc.last_viewed_at
            FROM user_comparisons uc
            JOIN comparison_cache cc ON uc.comparison_cache_id = cc.id
            WHERE uc.user_id = {p}
            ORDER BY uc.last_viewed_at DESC
            LIMIT {p}
        """, (user_id, limit))
        rows = cursor.fetchall()
        results = []
        for row in rows:
            item = _dict_from_row(row)
            item['language'] = item.get('language', 'en')
            # Calculate freshness
            if item.get('generated_at'):
                from datetime import datetime, timedelta
                generated = item['generated_at']
                if isinstance(generated, str):
                    generated = datetime.fromisoformat(generated.replace('Z', '+00:00').replace(' ', 'T'))
                item['is_outdated'] = (datetime.now() - generated.replace(tzinfo=None)) > timedelta(days=7)
                item['days_old'] = (datetime.now() - generated.replace(tzinfo=None)).days
            results.append(item)
        return results


# Initialize database on module import
init_database()
