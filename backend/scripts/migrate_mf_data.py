"""
Migrate MF data from SQLite to PostgreSQL.

Usage:
    # Local development (requires DATABASE_URL env var for PostgreSQL)
    python scripts/migrate_mf_data.py path/to/mf.db

    # Or with explicit DATABASE_URL
    DATABASE_URL=postgresql://... python scripts/migrate_mf_data.py path/to/mf.db

This script:
1. Creates the MF tables if they don't exist
2. Reads mutual_funds and calculated_returns from SQLite
3. Inserts/updates the data in PostgreSQL
"""

import os
import sys
import sqlite3
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg2
from psycopg2.extras import execute_batch

# Get DATABASE_URL from environment
DATABASE_URL = os.getenv("DATABASE_URL", "")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)


def create_tables(pg_conn):
    """Create MF tables in PostgreSQL."""
    cursor = pg_conn.cursor()

    # Read and execute migration SQL
    migration_path = Path(__file__).parent.parent.parent / "migrations" / "002_mf_analytics.sql"

    if migration_path.exists():
        print(f"Running migration from {migration_path}")
        with open(migration_path, 'r') as f:
            sql = f.read()
        cursor.execute(sql)
        pg_conn.commit()
        print("Tables created successfully")
    else:
        print(f"Migration file not found: {migration_path}")
        print("Creating tables inline...")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mutual_funds (
                id SERIAL PRIMARY KEY,
                scheme_code TEXT UNIQUE NOT NULL,
                scheme_name TEXT NOT NULL,
                fund_house TEXT,
                category TEXT,
                sub_category TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mf_calculated_returns (
                id SERIAL PRIMARY KEY,
                scheme_code TEXT NOT NULL REFERENCES mutual_funds(scheme_code) ON DELETE CASCADE,
                latest_nav REAL,
                latest_nav_date DATE,
                return_1m REAL,
                return_3m REAL,
                return_6m REAL,
                return_1y REAL,
                return_3y REAL,
                return_5y REAL,
                return_10y REAL,
                calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(scheme_code)
            )
        """)

        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_mf_scheme_code ON mutual_funds(scheme_code)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_mf_category ON mutual_funds(category)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_mf_sub_category ON mutual_funds(sub_category)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_mf_returns_scheme_code ON mf_calculated_returns(scheme_code)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_mf_returns_nav_date ON mf_calculated_returns(latest_nav_date DESC)")

        pg_conn.commit()
        print("Tables created inline")


def migrate_mutual_funds(sqlite_conn, pg_conn):
    """Migrate mutual_funds table."""
    print("\nMigrating mutual_funds...")

    # Read from SQLite
    sqlite_cursor = sqlite_conn.cursor()
    sqlite_cursor.execute("""
        SELECT scheme_code, scheme_name, fund_house, category, sub_category
        FROM mutual_funds
    """)
    rows = sqlite_cursor.fetchall()
    print(f"Read {len(rows)} funds from SQLite")

    # Insert into PostgreSQL
    pg_cursor = pg_conn.cursor()

    # Clear existing data (optional - comment out to do incremental updates)
    pg_cursor.execute("TRUNCATE mutual_funds CASCADE")
    print("Cleared existing mutual_funds data")

    # Batch insert
    insert_sql = """
        INSERT INTO mutual_funds (scheme_code, scheme_name, fund_house, category, sub_category)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (scheme_code) DO UPDATE SET
            scheme_name = EXCLUDED.scheme_name,
            fund_house = EXCLUDED.fund_house,
            category = EXCLUDED.category,
            sub_category = EXCLUDED.sub_category,
            updated_at = CURRENT_TIMESTAMP
    """

    execute_batch(pg_cursor, insert_sql, rows, page_size=1000)
    pg_conn.commit()

    # Verify
    pg_cursor.execute("SELECT COUNT(*) FROM mutual_funds")
    count = pg_cursor.fetchone()[0]
    print(f"Inserted {count} funds into PostgreSQL")


def migrate_calculated_returns(sqlite_conn, pg_conn):
    """Migrate calculated_returns table."""
    print("\nMigrating calculated_returns...")

    # Read from SQLite
    sqlite_cursor = sqlite_conn.cursor()
    sqlite_cursor.execute("""
        SELECT
            scheme_code,
            latest_nav,
            latest_nav_date,
            return_1m,
            return_3m,
            return_6m,
            return_1y,
            return_3y,
            return_5y,
            return_10y
        FROM calculated_returns
    """)
    rows = sqlite_cursor.fetchall()
    print(f"Read {len(rows)} return records from SQLite")

    # Insert into PostgreSQL
    pg_cursor = pg_conn.cursor()

    # Clear existing data
    pg_cursor.execute("TRUNCATE mf_calculated_returns")
    print("Cleared existing mf_calculated_returns data")

    # Batch insert
    insert_sql = """
        INSERT INTO mf_calculated_returns (
            scheme_code, latest_nav, latest_nav_date,
            return_1m, return_3m, return_6m, return_1y, return_3y, return_5y, return_10y
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (scheme_code) DO UPDATE SET
            latest_nav = EXCLUDED.latest_nav,
            latest_nav_date = EXCLUDED.latest_nav_date,
            return_1m = EXCLUDED.return_1m,
            return_3m = EXCLUDED.return_3m,
            return_6m = EXCLUDED.return_6m,
            return_1y = EXCLUDED.return_1y,
            return_3y = EXCLUDED.return_3y,
            return_5y = EXCLUDED.return_5y,
            return_10y = EXCLUDED.return_10y,
            calculated_at = CURRENT_TIMESTAMP
    """

    execute_batch(pg_cursor, insert_sql, rows, page_size=1000)
    pg_conn.commit()

    # Verify
    pg_cursor.execute("SELECT COUNT(*) FROM mf_calculated_returns")
    count = pg_cursor.fetchone()[0]
    print(f"Inserted {count} return records into PostgreSQL")


def main():
    if len(sys.argv) < 2:
        print("Usage: python migrate_mf_data.py <path_to_sqlite_db>")
        print("Example: python migrate_mf_data.py ../../MFAnalytics/data/mf.db")
        sys.exit(1)

    sqlite_path = sys.argv[1]

    if not os.path.exists(sqlite_path):
        print(f"Error: SQLite database not found: {sqlite_path}")
        sys.exit(1)

    if not DATABASE_URL:
        print("Error: DATABASE_URL environment variable not set")
        print("Set it to your PostgreSQL connection string, e.g.:")
        print("  export DATABASE_URL=postgresql://user:pass@host:5432/dbname")
        sys.exit(1)

    print(f"Source: {sqlite_path}")
    print(f"Target: PostgreSQL (DATABASE_URL)")
    print("-" * 50)

    # Connect to SQLite
    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row

    # Connect to PostgreSQL
    pg_conn = psycopg2.connect(DATABASE_URL)

    try:
        # Create tables
        create_tables(pg_conn)

        # Migrate data
        migrate_mutual_funds(sqlite_conn, pg_conn)
        migrate_calculated_returns(sqlite_conn, pg_conn)

        print("\n" + "=" * 50)
        print("Migration completed successfully!")
        print("=" * 50)

    except Exception as e:
        print(f"\nError during migration: {e}")
        pg_conn.rollback()
        raise
    finally:
        sqlite_conn.close()
        pg_conn.close()


if __name__ == "__main__":
    main()
