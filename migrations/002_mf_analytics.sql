-- Permabullish Database Schema
-- Migration 002: MF Analytics Tables
-- PostgreSQL

-- Create mutual_funds table
CREATE TABLE IF NOT EXISTS mutual_funds (
    id SERIAL PRIMARY KEY,
    scheme_code TEXT UNIQUE NOT NULL,
    scheme_name TEXT NOT NULL,
    fund_house TEXT,
    category TEXT,
    sub_category TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for mutual_funds
CREATE INDEX IF NOT EXISTS idx_mf_scheme_code ON mutual_funds(scheme_code);
CREATE INDEX IF NOT EXISTS idx_mf_category ON mutual_funds(category);
CREATE INDEX IF NOT EXISTS idx_mf_sub_category ON mutual_funds(sub_category);
CREATE INDEX IF NOT EXISTS idx_mf_fund_house ON mutual_funds(fund_house);
CREATE INDEX IF NOT EXISTS idx_mf_scheme_name ON mutual_funds(scheme_name);

-- Create calculated_returns table
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
);

-- Create indexes for calculated_returns
CREATE INDEX IF NOT EXISTS idx_mf_returns_scheme_code ON mf_calculated_returns(scheme_code);
CREATE INDEX IF NOT EXISTS idx_mf_returns_nav_date ON mf_calculated_returns(latest_nav_date DESC);

-- Notes:
--
-- mutual_funds: ~37,000 rows containing fund metadata
-- mf_calculated_returns: ~35,000 rows containing pre-calculated returns
--
-- Data is populated from AMFI via the migration script (migrate_mf_data.py)
-- Returns should be refreshed periodically via a cron job
