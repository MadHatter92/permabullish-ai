# Screener.in Data Integration Plan

**Created:** 2026-01-28
**Status:** Ready to implement
**Trigger:** Run overnight when ready

---

## Overview

Pre-scrape Nifty 500 stocks from Screener.in and cache fundamentals in PostgreSQL. Refresh monthly/quarterly since financial data doesn't change frequently.

## Why This Approach

| Data Type | Update Frequency | Source |
|-----------|------------------|--------|
| Quarterly Results | Every 3 months | Screener (cached DB) |
| Annual Financials | Once a year | Screener (cached DB) |
| Shareholding | Every quarter | Screener (cached DB) |
| Ratios (ROE, ROCE) | Quarterly | Screener (cached DB) |
| **Current Price** | **Real-time** | **Yahoo Finance (live)** |
| **Market Cap** | **Daily** | **Yahoo Finance (live)** |

**Key insight:** Separate static fundamentals (Screener, cached) from dynamic price data (Yahoo, live).

---

## Screener.in Verified Capabilities

- **No rate limiting** (tested 20 req/sec, all OK)
- **No Cloudflare/Captcha**
- **Works from cloud IPs** (tested via WebFetch)
- **robots.txt allows** `/company/*` pages
- **Response time:** ~180ms per request

### URL Pattern
```
https://www.screener.in/company/{SYMBOL}/consolidated/
https://www.screener.in/company/{SYMBOL}/
```

---

## Data Available from Screener

### 1. Key Metrics
- Market Cap, Current Price, 52W High/Low
- P/E, P/B, Book Value, Face Value
- Dividend Yield, ROCE, ROE

### 2. Quarterly Results (8-12 quarters)
- Sales, Expenses, Operating Profit, OPM %
- Other Income, Interest, Depreciation
- Profit Before Tax, Tax, Net Profit, EPS

### 3. Annual Financials (10+ years)
- **P&L:** Revenue, Expenses, EBITDA, PAT, EPS
- **Balance Sheet:** Equity, Reserves, Borrowings, Assets
- **Cash Flow:** Operating, Investing, Financing

### 4. Shareholding Pattern (quarterly history)
- Promoters, FIIs, DIIs, Government, Public

### 5. Key Ratios (historical)
- Debtor Days, Inventory Days, Days Payable
- Cash Conversion Cycle, Working Capital Days
- ROCE %, ROE % trends

### 6. Pros/Cons Analysis
- Auto-generated insights from Screener

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    REPORT GENERATION                     │
├─────────────────────────────────────────────────────────┤
│                                                          │
│   ┌──────────────┐         ┌──────────────────────┐     │
│   │ Yahoo Finance │ ──────▶ │ Real-time Price Data │     │
│   │   (Live API)  │         │ (price, volume, 52W) │     │
│   └──────────────┘         └──────────────────────┘     │
│                                                          │
│   ┌──────────────┐         ┌──────────────────────┐     │
│   │   PostgreSQL  │ ──────▶ │   Fundamentals Data  │     │
│   │  (Cached DB)  │         │ (P/E, ROE, quarters) │     │
│   └──────────────┘         └──────────────────────┘     │
│                                                          │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │   MONTHLY REFRESH    │
              │  (Screener Scraper)  │
              └─────────────────────┘
```

---

## Database Schema

```sql
-- Main fundamentals table (one row per company)
CREATE TABLE stock_fundamentals (
    id SERIAL PRIMARY KEY,
    symbol TEXT UNIQUE NOT NULL,
    company_name TEXT,
    sector TEXT,
    industry TEXT,

    -- Key Ratios (updated quarterly)
    pe_ratio REAL,
    pb_ratio REAL,
    dividend_yield REAL,
    roe REAL,
    roce REAL,
    debt_to_equity REAL,
    book_value REAL,
    face_value REAL,

    -- Quarterly Results (JSON array of last 12 quarters)
    quarterly_results JSONB,

    -- Annual Financials (JSON - P&L, Balance Sheet, Cash Flow)
    annual_financials JSONB,

    -- Shareholding Pattern (JSON array)
    shareholding JSONB,

    -- Historical Ratios
    historical_ratios JSONB,

    -- Pros/Cons Analysis
    pros TEXT[],
    cons TEXT[],

    -- Metadata
    screener_url TEXT,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_stock_fundamentals_symbol ON stock_fundamentals(symbol);
CREATE INDEX idx_stock_fundamentals_sector ON stock_fundamentals(sector);
```

---

## Sample JSONB Structure

```json
{
  "quarterly_results": [
    {
      "quarter": "Dec 2024",
      "sales": 216737,
      "expenses": 181728,
      "operating_profit": 35009,
      "opm_percent": 16.2,
      "net_profit": 18540,
      "eps": 27.35
    }
  ],
  "shareholding": [
    {
      "quarter": "Dec 2024",
      "promoters": 50.0,
      "fiis": 19.09,
      "diis": 20.10,
      "public": 10.64
    }
  ],
  "annual_financials": {
    "profit_loss": [...],
    "balance_sheet": [...],
    "cash_flow": [...]
  }
}
```

---

## Implementation Steps

### Step 1: Create Scraper Script
**File:** `backend/scripts/scrape_screener.py`

```python
# Pseudocode structure
def scrape_screener():
    symbols = get_nifty500_symbols()  # From NSE or existing list

    for symbol in symbols:
        html = fetch_screener_page(symbol)
        data = parse_all_sections(html)
        save_to_database(symbol, data)
        time.sleep(0.5)  # Be nice

    print(f"Scraped {len(symbols)} stocks")
```

**Parsing functions needed:**
- `parse_key_metrics(soup)` → dict
- `parse_quarterly_results(soup)` → list[dict]
- `parse_annual_financials(soup)` → dict
- `parse_shareholding(soup)` → list[dict]
- `parse_ratios(soup)` → list[dict]
- `parse_pros_cons(soup)` → dict

### Step 2: Database Integration
**File:** `backend/screener_db.py`

```python
def get_fundamentals(symbol: str) -> dict:
    """Get cached fundamentals from DB."""

def refresh_stock(symbol: str) -> dict:
    """Scrape and update single stock."""

def get_stale_stocks(days: int = 30) -> list:
    """Get stocks not updated in N days."""

def bulk_refresh() -> dict:
    """Full Nifty 500 refresh."""
```

### Step 3: Update Report Generator
**File:** `backend/report_generator.py`

```python
# Current flow:
# Yahoo Finance → fundamentals + price

# New flow:
# Yahoo Finance → price data only
# PostgreSQL → fundamentals (cached from Screener)
# Merge both for complete data
```

### Step 4: Add Database Migration
**File:** `migrations/003_stock_fundamentals.sql`

### Step 5: Schedule Monthly Refresh
- Render Cron Job OR
- Background task on first request of month

---

## Refresh Strategy

| Trigger | Action |
|---------|--------|
| **Monthly cron** | Full refresh of all 500 stocks |
| **Post-earnings** | Priority refresh (Apr, Jul, Oct, Jan) |
| **On-demand** | If data > 45 days old, refresh that stock |
| **New stock request** | Scrape & cache if not in DB |

---

## Estimated Runtime

- 500 stocks × 0.5s delay = ~4-5 minutes
- With parsing overhead = ~8-10 minutes total
- Run overnight or during low-traffic hours

---

## Files to Create/Modify

| File | Action |
|------|--------|
| `backend/scripts/scrape_screener.py` | NEW - Main scraper |
| `backend/screener_db.py` | NEW - DB operations |
| `migrations/003_stock_fundamentals.sql` | NEW - Schema |
| `backend/report_generator.py` | MODIFY - Use cached data |
| `backend/database.py` | MODIFY - Add fundamentals queries |

---

## Benefits

1. **Fast reports** - No scraping delay during generation
2. **Reliable** - Data always available, no scraping failures
3. **Respectful** - Only 500 requests/month to Screener
4. **Queryable** - Can add sector analysis, peer comparison
5. **Historical** - Can track changes over time

---

## To Start Implementation

Just tell Claude: **"Let's implement the Screener scraper from the plan"**

The conversation context + this file has everything needed.
