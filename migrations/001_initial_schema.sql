-- Permabullish Database Schema
-- Migration 001: Initial Schema
-- PostgreSQL

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT,
    full_name TEXT NOT NULL,
    google_id TEXT UNIQUE,
    auth_provider TEXT DEFAULT 'local',
    avatar_url TEXT,
    subscription_tier TEXT DEFAULT 'free',  -- free, pro, enterprise
    stripe_customer_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- Create index for faster email lookups
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_google_id ON users(google_id);

-- Create reports table
CREATE TABLE IF NOT EXISTS reports (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    company_name TEXT NOT NULL,
    ticker TEXT NOT NULL,
    exchange TEXT DEFAULT 'NSE',
    sector TEXT,
    current_price REAL,
    target_price REAL,
    recommendation TEXT,
    report_html TEXT NOT NULL,
    report_data TEXT,  -- JSON blob with full stock data and analysis
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index for faster user report lookups
CREATE INDEX IF NOT EXISTS idx_reports_user_id ON reports(user_id);
CREATE INDEX IF NOT EXISTS idx_reports_created_at ON reports(created_at DESC);

-- Create usage tracking table
CREATE TABLE IF NOT EXISTS usage (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    month_year TEXT NOT NULL,  -- Format: YYYY-MM
    reports_generated INTEGER DEFAULT 0,
    UNIQUE(user_id, month_year)
);

-- Create index for usage lookups
CREATE INDEX IF NOT EXISTS idx_usage_user_month ON usage(user_id, month_year);

-- Create anonymous usage tracking table
CREATE TABLE IF NOT EXISTS anonymous_usage (
    id SERIAL PRIMARY KEY,
    identifier TEXT UNIQUE NOT NULL,  -- Hashed IP address
    reports_generated INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create usage limits table (for subscription tiers / paywall)
CREATE TABLE IF NOT EXISTS usage_limits (
    id SERIAL PRIMARY KEY,
    tier TEXT UNIQUE NOT NULL,
    monthly_reports INTEGER NOT NULL,
    features JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert default subscription tiers
INSERT INTO usage_limits (tier, monthly_reports, features) VALUES
    ('free', 20, '{"stock_research": true, "mf_analytics": false, "pms_tracker": false, "api_access": false}'),
    ('pro', 100, '{"stock_research": true, "mf_analytics": true, "pms_tracker": true, "api_access": false}'),
    ('enterprise', 1000, '{"stock_research": true, "mf_analytics": true, "pms_tracker": true, "api_access": true}')
ON CONFLICT (tier) DO NOTHING;

-- Create anonymous user (user_id = 0) for anonymous reports
-- This is a special system user
INSERT INTO users (id, email, password_hash, full_name, auth_provider, subscription_tier)
VALUES (0, 'anonymous@system.local', NULL, 'Anonymous User', 'system', 'free')
ON CONFLICT (id) DO NOTHING;

-- Reset the sequence to start after the anonymous user
SELECT setval('users_id_seq', (SELECT COALESCE(MAX(id), 0) FROM users) + 1, false);

-- ================================================================
-- FUTURE MIGRATIONS (Phase 2+)
-- ================================================================

-- Phase 2: PMS Tracker tables (uncomment when ready)
/*
CREATE TABLE IF NOT EXISTS pms_schemes (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    manager TEXT NOT NULL,
    aum REAL,
    min_investment REAL,
    fees TEXT,
    strategy TEXT,
    benchmark TEXT,
    inception_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS pms_performance (
    id SERIAL PRIMARY KEY,
    scheme_id INTEGER NOT NULL REFERENCES pms_schemes(id) ON DELETE CASCADE,
    period TEXT NOT NULL,  -- 1m, 3m, 6m, 1y, 3y, 5y, si
    return_pct REAL,
    benchmark_return_pct REAL,
    alpha REAL,
    recorded_at DATE DEFAULT CURRENT_DATE
);
*/

-- Phase 3: MF Analytics tables (uncomment when ready)
/*
CREATE TABLE IF NOT EXISTS mf_schemes (
    id SERIAL PRIMARY KEY,
    scheme_code TEXT UNIQUE NOT NULL,
    scheme_name TEXT NOT NULL,
    amc TEXT,
    category TEXT,
    sub_category TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS mf_metrics (
    id SERIAL PRIMARY KEY,
    scheme_id INTEGER NOT NULL REFERENCES mf_schemes(id) ON DELETE CASCADE,
    nav REAL,
    aum REAL,
    expense_ratio REAL,
    sharpe_ratio REAL,
    sortino_ratio REAL,
    max_drawdown REAL,
    volatility REAL,
    return_1y REAL,
    return_3y REAL,
    return_5y REAL,
    computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Monthly sampled NAV data (to reduce storage)
CREATE TABLE IF NOT EXISTS mf_nav_monthly (
    id SERIAL PRIMARY KEY,
    scheme_id INTEGER NOT NULL REFERENCES mf_schemes(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    nav REAL NOT NULL,
    UNIQUE(scheme_id, date)
);
*/

-- Phase 4: Stripe/Payments tables (uncomment when ready)
/*
CREATE TABLE IF NOT EXISTS subscriptions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    stripe_subscription_id TEXT UNIQUE,
    tier TEXT NOT NULL,
    status TEXT DEFAULT 'active',  -- active, canceled, past_due
    current_period_start TIMESTAMP,
    current_period_end TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS payments (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    stripe_payment_intent_id TEXT UNIQUE,
    amount_cents INTEGER NOT NULL,
    currency TEXT DEFAULT 'inr',
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
*/
