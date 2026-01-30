# Permabullish - AI Stock Researcher
## Product Requirements Document (PRD)

**Version:** 2.0
**Date:** January 30, 2025
**Status:** Active Development

---

## 1. Executive Summary

Permabullish is an AI-powered stock research platform for Indian equities. Users can generate professional-grade equity research reports using Claude AI, with reports covering investment thesis, valuation analysis, bull/bear cases, and actionable recommendations.

The product operates on a subscription model with tiered access, allowing users to generate a specified number of reports per month based on their subscription level.

---

## 2. Product Vision

**Mission:** Democratize professional equity research for Indian retail investors.

**Value Proposition:** Get institutional-quality stock research reports instantly, powered by AI, at a fraction of the cost of traditional research services.

---

## 3. Target Users

- **Primary:** Indian retail investors researching NSE/BSE stocks
- **Secondary:** Financial advisors, wealth managers, and investment enthusiasts
- **Geography:** India (initial focus)

---

## 4. Core Features

### 4.1 Stock Research Reports

**Report Contents:**
- Investment recommendation (STRONG BUY / BUY / HOLD / SELL / STRONG SELL)
- AI-recommended target price
- Conviction level
- Investment thesis
- Bull case / Bear case analysis
- Key risks and catalysts
- Quarterly results analysis
- News impact assessment
- Competitive advantages
- Financial metrics and valuation

**Report Freshness:**
- Reports always display generation date prominently
- **First-time viewer + report >15 days old:** Auto-generate fresh report (consumes quota)
- **Returning viewer + report >15 days old:** Show cached report with "Regenerate" option
- **Any report >15 days old:** Show "Regenerate Report" button
- Regenerating a report consumes 1 from user's quota
- Cached reports are shared across all users for efficiency

**Languages:**
- Phase 1: English only
- Phase 2: Hindi, Gujarati (dropdown selection)

### 4.2 User Dashboard

**Key Elements:**
| Element | Description |
|---------|-------------|
| Current Price | Real-time stock price from Yahoo Finance |
| AI Recommended Price | Target price from AI analysis |
| User's Target Price | User-editable field for personal target |
| Report | Link to view/regenerate full report |
| Watchlist | Stocks being tracked |
| Report History | Previously generated/viewed reports |

### 4.3 Watchlist

- Users can save stocks to track
- Visual indicator for stocks without reports
- One-click report generation from watchlist
- Sorted by date added (newest first)

### 4.4 Report History

- List of all reports generated/viewed by user
- Shows: Stock name, ticker, generation date, recommendation
- Visual badge for outdated reports (>15 days)
- Quick actions: View, Regenerate, Delete

---

## 5. Subscription Tiers

### 5.1 Tier Structure

| Tier | Reports | Price (TBD) | Features |
|------|---------|-------------|----------|
| **Free** | 3 total (lifetime) | Free | Basic access, Google sign-in |
| **Basic** | 10/month | TBD | Full reports, watchlist, history |
| **Pro** | 50/month | TBD | All Basic features + priority generation |
| **Enterprise** | Unlimited | Contact us | All features + dedicated support |

**Note:** Pricing will be calculated based on token consumption analysis (see Roadmap Phase 5).

### 5.2 Payment Options

| Period | Discount | Billing |
|--------|----------|---------|
| 1 Month | None | Monthly |
| 6 Months | TBD% | Upfront |
| 12 Months | TBD% | Upfront |

**Payment Gateway:** Cashfree
- Initial implementation: Upfront payments only
- Future: Recurring subscription handling

### 5.3 Quota Management

- Usage resets on the 1st of each month (for paid tiers)
- Free tier: Lifetime limit of 3 reports
- Unused reports do NOT roll over
- Regenerating a cached report counts against quota

---

## 6. Data Sources

### 6.1 Stock Data

| Source | Data Type | Frequency |
|--------|-----------|-----------|
| **Screener.in** | Fundamentals, financials, ratios | Monthly scrape |
| **Yahoo Finance** | Real-time prices, basic metrics | On-demand |
| **NSE/BSE** | Corporate actions, announcements | As needed |

### 6.2 AI Analysis

- **Model:** Claude (Anthropic API)
- **Purpose:** Generate opinionated investment analysis
- **Input:** Stock data from above sources
- **Output:** Structured JSON converted to HTML report

---

## 7. Authentication & Security

### 7.1 Authentication

- **Primary:** Google OAuth 2.0
- **Session:** JWT tokens (7-day expiry)
- **No email/password:** Google sign-in only for simplicity

### 7.2 Security Considerations

- All API endpoints require authentication (except health check)
- Rate limiting on report generation
- No storage of payment credentials (handled by Cashfree)
- HTTPS only in production

---

## 8. Technical Architecture

### 8.1 Stack

| Layer | Technology |
|-------|------------|
| **Backend** | FastAPI (Python 3.11+) |
| **Database** | PostgreSQL (production) / SQLite (development) |
| **Frontend** | Static HTML/CSS/JS + Tailwind CSS |
| **AI** | Anthropic Claude API |
| **Auth** | Google OAuth + JWT |
| **Payments** | Cashfree |
| **Hosting** | Render |

### 8.2 API Endpoints

**Authentication:**
- `GET /api/auth/google/login` - Initiate Google OAuth
- `GET /api/auth/google/callback` - OAuth callback
- `GET /api/auth/me` - Get current user

**Reports:**
- `GET /api/stocks/search?q=` - Search Indian stocks
- `GET /api/stocks/{symbol}` - Get stock preview
- `POST /api/reports/generate` - Generate report (consumes quota)
- `GET /api/reports` - List user's reports
- `GET /api/reports/{id}` - Get report details
- `GET /api/reports/{id}/html` - Get report HTML
- `DELETE /api/reports/{id}` - Remove from history

**Report Cache:**
- `GET /api/reports/cached/{ticker}` - Get cached report if exists
- Reports cached by ticker, shared across users

**Watchlist:**
- `GET /api/watchlist` - Get user's watchlist
- `POST /api/watchlist` - Add stock to watchlist
- `DELETE /api/watchlist/{ticker}` - Remove from watchlist

**User:**
- `GET /api/user/profile` - Get profile with subscription info
- `PUT /api/user/target-price` - Set user's target price for a stock
- `GET /api/usage` - Get usage stats

**Subscription:**
- `GET /api/subscription/plans` - Get available plans
- `POST /api/subscription/checkout` - Initiate Cashfree checkout
- `POST /api/subscription/webhook` - Cashfree payment webhook
- `GET /api/subscription/status` - Get subscription status

**Health:**
- `GET /api/health` - Service health check

### 8.3 Database Schema

```sql
-- Users
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    google_id VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    avatar_url TEXT,
    subscription_tier VARCHAR(50) DEFAULT 'free',
    subscription_expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- Subscriptions
CREATE TABLE subscriptions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    tier VARCHAR(50) NOT NULL,
    period_months INTEGER NOT NULL,
    amount_paid DECIMAL(10,2),
    currency VARCHAR(3) DEFAULT 'INR',
    payment_id VARCHAR(255),
    starts_at TIMESTAMP NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Report Cache (shared across users)
CREATE TABLE report_cache (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(20) NOT NULL,
    exchange VARCHAR(10) NOT NULL,
    company_name VARCHAR(255),
    report_html TEXT,
    report_data JSONB,
    recommendation VARCHAR(50),
    ai_target_price DECIMAL(10,2),
    current_price DECIMAL(10,2),
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(ticker, exchange)
);

-- User Report Access (tracks which reports user has viewed)
CREATE TABLE user_reports (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    report_cache_id INTEGER REFERENCES report_cache(id),
    user_target_price DECIMAL(10,2),
    first_viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Usage Tracking
CREATE TABLE usage (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    month_year VARCHAR(7) NOT NULL, -- e.g., '2025-01'
    reports_generated INTEGER DEFAULT 0,
    UNIQUE(user_id, month_year)
);

-- Watchlist
CREATE TABLE watchlist (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    ticker VARCHAR(20) NOT NULL,
    exchange VARCHAR(10) NOT NULL,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, ticker, exchange)
);

-- Screener Data Cache
CREATE TABLE screener_data (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(20) NOT NULL,
    exchange VARCHAR(10) NOT NULL,
    data JSONB,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(ticker, exchange)
);
```

---

## 9. Design System

### 9.1 Brand Colors

**Primary Palette:**
| Name | Hex | Usage |
|------|-----|-------|
| Navy 950 | `#102a43` | Page background |
| Navy 900 | `#1e3a5f` | Card backgrounds, header |
| Navy 700 | `#334e68` | Borders, secondary elements |
| Saffron 500 | `#e8913a` | Primary CTA, brand accent |
| Saffron 600 | `#d97316` | Hover states |

**Text Colors:**
| Name | Hex | Usage |
|------|-----|-------|
| White | `#ffffff` | Primary text on dark bg |
| Navy 300 | `#9fb3c8` | Secondary text |
| Navy 400 | `#829ab1` | Muted text |

### 9.2 Typography

| Style | Font | Weight | Size |
|-------|------|--------|------|
| Display | DM Serif Display | Regular | 36-48px |
| Heading | DM Sans | Bold | 24-32px |
| Body | DM Sans / Inter | Regular | 14-16px |
| Caption | Inter | Regular | 12px |

### 9.3 Component Patterns

**Cards:**
```css
background: linear-gradient(to bottom right, #1e3a5f, #243b53);
border: 1px solid #334e68;
border-radius: 1rem;
```

**Primary Button:**
```css
background: #e8913a;
color: white;
border-radius: 0.75rem;
padding: 0.75rem 1.5rem;
hover: background #d97316;
```

**Secondary Button:**
```css
background: #243b53;
color: white;
border-radius: 0.75rem;
hover: background #334e68;
```

---

## 10. Future Considerations (Not in Initial Scope)

- **Chat with AI:** Ask follow-up questions about a stock
- **Portfolio tracking:** Track holdings and performance
- **Alerts:** Price alerts, report refresh notifications
- **API access:** Enterprise tier programmatic access
- **Mobile app:** Native iOS/Android apps
- **International stocks:** US, UK, other markets

---

## 11. Success Metrics

| Metric | Target |
|--------|--------|
| User signups (Month 1) | 500 |
| Free to paid conversion | 5% |
| Reports generated/day | 100 |
| User retention (30-day) | 40% |
| Average reports/user | 5 |

---

## 12. Contact

**Product:** Permabullish
**Enterprise inquiries:** mail@mayaskara.com
**Website:** permabullish.com

---

*This document is a living specification and will be updated as the product evolves.*
