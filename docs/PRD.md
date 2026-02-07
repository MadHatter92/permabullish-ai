# Permabullish - AI Stock Researcher
## Product Requirements Document (PRD)

**Version:** 2.6
**Date:** February 7, 2026
**Status:** Phase 1-4 Complete, Phase 7 Complete, Phase 5 Partially Complete, Email/Password Auth Complete

---

## 1. Executive Summary

Permabullish is an AI-powered stock research platform for Indian equities. Users can generate professional-grade equity research reports using Claude AI, with reports covering investment thesis, valuation analysis, bull/bear cases, and actionable recommendations.

The product operates on a subscription model with tiered access, allowing users to generate a specified number of reports per month based on their subscription level.

---

## 2. Implementation Status

### Phase 0: Repository Cleanup ✅ (Completed Jan 30, 2026)
- Archived MF Analytics, PMS Tracker, and Landing page code
- Updated render.yaml to remove obsolete services
- Focused repository on single product: AI Stock Researcher

### Phase 1: Core Product Enhancement ✅ (Completed Jan 30, 2026)

| Feature | Status | Notes |
|---------|--------|-------|
| Report Caching System | ✅ Done | Shared cache across all users |
| 15-day Freshness Logic | ✅ Done | Auto-regenerate for first-time viewers |
| Regenerate Button | ✅ Done | For outdated reports (>15 days) |
| Watchlist Feature | ✅ Done | Add/remove stocks, CRUD API |
| User Target Price | ✅ Done | Editable per-report target |
| Dashboard Tabs | ✅ Done | Reports & Watchlist views |
| Report Info Bar | ✅ Done | Shows date, AI target, user target |
| Database Init on Startup | ✅ Done | Auto-creates tables |
| PostgreSQL Compatibility | ✅ Done | Fixed row access patterns |
| CORS Configuration | ✅ Done | Production URLs always included |
| Admin Reset Endpoint | ✅ Done | For testing: `/api/admin/reset-usage` |

**Backend Changes:**
- `database.py`: Added `report_cache`, `user_reports`, `watchlist` tables
- `database.py`: Added caching functions, watchlist CRUD, user target price
- `main.py`: Updated report generation to use caching
- `main.py`: Added watchlist endpoints, user target price endpoint
- `config.py`: Updated subscription tiers, CORS origins

**Frontend Changes:**
- `dashboard.html`: Tabs for Reports/Watchlist, freshness indicators
- `generate.html`: Watchlist toggle, cached report notice, URL params
- `report.html`: Info bar with date, targets, regenerate button
- `config.js`: Updated tier limits, added freshness config

### Phase 2: Subscription System (Partially Complete)
- ✅ Enforce tier limits in UI (expired banners)
- ✅ Upgrade prompts and flows
- ⏳ Subscription management page (deferred until payments)

### Phase 3: Payment Integration ✅ (Completed Jan 30, 2026)
- ✅ Cashfree integration (sandbox + production)
- ✅ Payment order creation API
- ✅ Payment verification endpoint
- ✅ Webhook handler for payment events
- ✅ Subscription activation on successful payment
- ✅ Checkout page with Cashfree JS SDK
- ✅ Payment status page (success/failed/pending states)
- ⏳ Paying vs non-paying user tracking (Phase 6)

### Phase 4: Data Pipeline (Pending)
- Screener.in scraper
- Monthly data refresh cron

### Phase 5: Pricing Analysis (Partially Complete)
- ✅ Token consumption tracking (per report)
- ✅ Cost estimation (~₹3/report baseline)
- ✅ Enhanced cron reports with cost data
- ⏳ Final pricing tiers (pending business decision)

### Phase 6: Analytics & User Tracking (Pending)
- Guest-to-signup attribution (link anonymous usage to new accounts)
- Session duration tracking (login/activity timestamps)
- Event logging (searches, report views, feature usage)
- Cohort analysis support (acquisition source, first actions)
- Conversion funnel metrics (guest → free → paid)
- Churn and retention tracking

---

## 3. Product Vision

**Mission:** Democratize professional equity research for Indian retail investors.

**Value Proposition:** Get institutional-quality stock research reports instantly, powered by AI, at a fraction of the cost of traditional research services.

---

## 4. Target Users

- **Primary:** Indian retail investors researching NSE/BSE stocks
- **Secondary:** Financial advisors, wealth managers, and investment enthusiasts
- **Tertiary:** Stock brokers, sub-brokers, and Associated Persons (APs) serving retail clients
- **Geography:** India (initial focus)
- **Languages:** English, Hindi (हिंदी), Gujarati (ગુજરાતી)

---

## 5. Core Features

### 5.1 Stock Research Reports

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
- English, Hindi, Gujarati (toggle selection on generate page)

### 5.5 Stock Comparison Tool

**Purpose:** Compare two stocks side-by-side with AI-powered verdict on which to invest in.

**Comparison Contents:**
- AI Verdict (which stock wins + conviction level)
- One-line verdict summary
- Key differentiators (Valuation, Growth, Quality, Risk)
- Metrics comparison table with winner highlights
- "Who should buy which" guidance
- Links to full individual reports

**Features:**
- Dual stock selector with search
- Language support (EN, Hindi, Gujarati)
- Cached comparisons (view history in dashboard)
- Social sharing with OG image previews
- Costs 1 report credit per comparison

**UI Elements:**
- Verdict banner with trophy icon
- Color-coded metrics table (green = winner)
- Sticky bottom share bar
- Mobile responsive layout

### 5.2 User Dashboard

**Key Elements:**
| Element | Description |
|---------|-------------|
| Current Price | Real-time stock price from Yahoo Finance |
| AI Recommended Price | Target price from AI analysis |
| User's Target Price | User-editable field for personal target |
| Report | Link to view/regenerate full report |
| Watchlist | Stocks being tracked |
| Report History | Previously generated/viewed reports |

### 5.3 Watchlist

- Users can save stocks to track
- Visual indicator for stocks without reports
- One-click report generation from watchlist
- Sorted by date added (newest first)

### 5.4 Report History

- List of all reports generated/viewed by user
- Shows: Stock name, ticker, generation date, recommendation
- Visual badge for outdated reports (>15 days)
- Quick actions: View, Regenerate, Delete

---

## 6. Subscription Tiers

### 6.1 Tier Structure

| Tier | Reports | Features |
|------|---------|----------|
| **Guest** | 1 (lifetime) | Basic access, no account required |
| **Free** | 5 (lifetime) | Full reports, watchlist, history |
| **Basic** | 50/month | All Free features |
| **Pro** | 100/month | All Basic + priority generation |
| **Enterprise** | Unlimited | All features + API access + dedicated support |

### 6.2 Target Audience Segments

| Segment | Description | Email Approach |
|---------|-------------|----------------|
| **Retail Investors** | Individual stock traders | Educational, feature highlights |
| **Brokers & Sub-Brokers** | Stock brokers, sub-brokers, Associated Persons (APs) | Client tools, time savings, competitive edge |
| **Regional Users** | Hindi and Gujarati speaking investors | Multilingual content, regional relevance |

### 6.3 Pricing (INR)

| Tier | Monthly | 6 Months | Yearly | Per Report |
|------|---------|----------|--------|------------|
| **Guest** | Free | - | - | - |
| **Free** | Free | - | - | - |
| **Basic** | ₹999 | ~~₹6,000~~ ₹3,999 | ~~₹12,000~~ ₹7,499 | ₹12.50-₹20 |
| **Pro** | ₹1,499 | ~~₹9,000~~ ₹5,999 | ~~₹18,000~~ ₹9,999 | ₹8.33-₹15 |
| **Enterprise** | Contact us | - | - | - |

**Savings:**
- 6 Months: 33% off monthly price
- Yearly: 38% off (Basic) / 44% off (Pro)

**Payment Gateway:** Cashfree
- Accepts UPI, credit/debit cards, net banking
- Upfront payments (no recurring subscriptions yet)

### 6.3 Quota Management

- Usage resets on the 1st of each month (for paid tiers)
- Guest tier: Lifetime limit of 1 report
- Free tier: Lifetime limit of 5 reports
- Unused reports do NOT roll over
- Regenerating a cached report counts against quota

---

## 7. Email Marketing System

### 7.1 Email Types

| Email Type | Trigger | Purpose |
|------------|---------|---------|
| **Welcome** | User signup | Onboard new users, showcase features |
| **Purchase Confirmation** | Subscription activated | Confirm plan details and benefits |
| **Re-engagement** | Inactivity (7+ days) | Win back inactive users |
| **Expiry Reminder** | Subscription ending | Encourage renewal |

### 7.2 Re-engagement Email Templates (14 + 1 Weekly)

| # | Type | Subject | Audience |
|---|------|---------|----------|
| 1 | Generic | Your AI research reports are waiting | All |
| 2 | Broker | The research tool smart brokers are using | Brokers, Sub-brokers, APs |
| 3 | Generic | What smart investors look for | All |
| 4 | Broker | 2 hours of research in 30 seconds | Brokers, Sub-brokers, APs |
| 5 | Generic | Investors are researching these stocks | All |
| 6 | Broker | Institutional research for independent brokers | Brokers, Sub-brokers, APs |
| 7 | Hindi | अब हिंदी में AI स्टॉक रिसर्च | Hindi speakers |
| 8 | Gujarati | હવે ગુજરાતીમાં AI સ્ટોક રિસર્ચ | Gujarati speakers |
| 9 | Generic | Markets moved this week | All |
| 10 | Broker | Your competition is using AI research | Brokers, Sub-brokers, APs |
| 11 | Hindi | आपके Hindi-speaking clients के लिए | Hindi speakers (broker angle) |
| 12 | Gujarati | તમારા Gujarati-speaking clients માટે | Gujarati speakers (broker angle) |
| 13 | Generic | Did you know Permabullish can do this? | All |
| 14 | Broker | Better research = more client trades | Brokers, Sub-brokers, APs |
| 15 | Weekly | Weekly: Your AI market insights | All (weekly digest) |

### 7.3 Re-engagement Eligibility Criteria

A registered user receives re-engagement emails only when ALL of the following conditions are met:

| Criterion | Requirement | Rationale |
|-----------|-------------|-----------|
| **Account Status** | `is_active = TRUE` | Deactivated accounts are excluded |
| **Subscription Tier** | `subscription_tier = 'free'` | Paid users excluded (they get expiry reminders instead) |
| **Account Age** | Signed up within 180 days | Focus on recent signups with conversion potential |
| **Inactivity** | No activity for 7+ days | Only target users who haven't engaged recently |
| **Email Timing** | See schedule below | Prevent email fatigue |

**Activity Tracking:**
- `last_activity_at` is updated when users generate reports or compare stocks
- Login alone does NOT count as activity (prevents gaming the system)
- New users start with `last_activity_at` = signup time

**Why a user might NOT receive re-engagement emails:**
1. They're on a paid tier (basic, pro, enterprise)
2. They've been active within the last 7 days
3. They already received an email today (daily phase) or this week (weekly phase)
4. Their account is older than 180 days
5. Their account is deactivated

### 7.4 Email Schedule

- **Days 1-14 after signup (Daily Phase):**
  - One email per day maximum
  - Only if inactive for 7+ days
  - Templates 1-14 rotate in sequence
- **Days 15-180 after signup (Weekly Phase):**
  - One email per week maximum
  - Only if inactive for 7+ days
  - Template 15 (weekly digest) used
- Templates rotate: 1→2→3→...→14→1→...

### 7.5 External Contacts System

Support for bulk email campaigns to external contact lists (not registered users):

| Feature | Description |
|---------|-------------|
| **Import** | CSV import via `scripts/import_external_contacts.py` |
| **Eligibility** | All active contacts (no inactivity requirement) |
| **Template Rotation** | Same 14 templates as registered users |
| **Cleanup** | Bounce detection via `scripts/cleanup_bounced_emails.py` |
| **Rate Limiting** | 0.6s delay between emails (Resend API: 2 req/sec) |

**Key Difference from Registered Users:**
- External contacts receive emails regardless of activity (no 7-day inactivity requirement)
- They don't have accounts, so there's no activity to track
- Template rotation is based on `reengagement_email_count` only

### 7.6 Batched Email Sending

External contacts are split into 3 batches for better email delivery:

| Batch | Time (IST) | Time (UTC) | Description |
|-------|------------|------------|-------------|
| 0 | 9:00 AM | 3:30 AM | Morning batch |
| 1 | 2:00 PM | 8:30 AM | Afternoon batch |
| 2 | 6:00 PM | 12:30 PM | Evening batch |

**Rotation Formula:** `(contact_id + day_of_year) % 3`

This ensures:
- Each contact receives emails at different times on different days
- Batch assignment rotates daily for variety
- Email delivery is spread throughout the day

**Example:**
- Day 1 (day_of_year=1): Contact ID 100 → (100+1)%3 = 2 → Evening batch
- Day 2 (day_of_year=2): Contact ID 100 → (100+2)%3 = 0 → Morning batch
- Day 3 (day_of_year=3): Contact ID 100 → (100+3)%3 = 1 → Afternoon batch

### 7.7 Email Infrastructure

- **Provider:** Resend (SMTP alternative to SendGrid)
- **Sending Domain:** permabullish.com (SPF, DKIM verified)
- **Batch Size Limit:** 200 emails/batch (configurable via `--batch-size`)
- **Cron Jobs:**
  - Re-engagement Morning: 9 AM IST (Batch 0, max 200)
  - Re-engagement Afternoon: 2 PM IST (Batch 1, max 200)
  - Re-engagement Evening: 6 PM IST (Batch 2, max 200)
  - Bounce cleanup: 8:30 PM IST daily
  - Expiry reminders: 10:30 AM IST daily

---

## 8. Data Sources

### 8.1 Stock Data

| Source | Data Type | Frequency |
|--------|-----------|-----------|
| **Screener.in** | Fundamentals, financials, ratios | Monthly scrape |
| **Yahoo Finance** | Real-time prices, basic metrics | On-demand |
| **NSE/BSE** | Corporate actions, announcements | As needed |

### 8.2 AI Analysis

- **Model:** Claude (Anthropic API)
- **Purpose:** Generate opinionated investment analysis
- **Input:** Stock data from above sources
- **Output:** Structured JSON converted to HTML report

---

## 9. Authentication & Security

### 9.1 Authentication

- **Google OAuth 2.0:** Primary sign-in method, auto-verified emails
- **Email/Password:** Full registration flow with email verification
  - Registration sends verification email (24-hour expiry token)
  - Users must verify email before signing in
  - Password hashing via pbkdf2_sha256
- **Password Reset:** Forgot password flow with reset tokens (1-hour expiry)
- **Account Linking:** If a user registers with email/password and later signs in with Google (same email), accounts are linked automatically
- **Session:** JWT tokens (7-day expiry)

### 9.2 Security Considerations

- All API endpoints require authentication (except health check)
- Rate limiting on report generation and auth endpoints
- Email verification required before account access
- Password reset tokens are single-purpose and time-limited
- Auth responses never reveal whether an email exists (forgot-password, resend-verification)
- No storage of payment credentials (handled by Cashfree)
- HTTPS only in production

---

## 10. Technical Architecture

### 10.1 Stack

| Layer | Technology |
|-------|------------|
| **Backend** | FastAPI (Python 3.11+) |
| **Database** | PostgreSQL (production) / SQLite (development) |
| **Frontend** | Static HTML/CSS/JS + Tailwind CSS |
| **AI** | Anthropic Claude API |
| **Auth** | Google OAuth + Email/Password + JWT |
| **Payments** | Cashfree |
| **Hosting** | Render |

### 10.2 API Endpoints

**Authentication:**
- `POST /api/auth/register` - Register with email/password (sends verification email)
- `POST /api/auth/login` - Sign in with email/password
- `GET /api/auth/google/login` - Initiate Google OAuth
- `GET /api/auth/google/callback` - OAuth callback
- `GET /api/auth/verify-email?token=` - Verify email (redirects to frontend)
- `POST /api/auth/resend-verification` - Resend verification email
- `POST /api/auth/forgot-password` - Request password reset email
- `POST /api/auth/reset-password` - Reset password with token
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

**Comparisons:**
- `POST /api/reports/compare` - Generate stock comparison
- `GET /api/comparisons` - Get user's comparison history
- `GET /api/comparisons/{id}` - Get specific comparison
- `GET /api/comparisons/{id}/og-image` - OG image for sharing
- `GET /api/comparisons/{id}/share` - Share page with OG meta tags

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

### 10.3 Database Schema

```sql
-- Users
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    google_id VARCHAR(255) UNIQUE,
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255),
    avatar_url TEXT,
    password_hash TEXT,
    auth_provider VARCHAR(20) DEFAULT 'email',
    email_verified BOOLEAN DEFAULT FALSE,
    subscription_tier VARCHAR(50) DEFAULT 'free',
    subscription_expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    last_activity_at TIMESTAMP,
    welcome_email_sent BOOLEAN DEFAULT FALSE,
    last_reengagement_email_at TIMESTAMP,
    reengagement_email_count INTEGER DEFAULT 0
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

-- Comparison Cache (shared across users)
CREATE TABLE comparison_cache (
    id SERIAL PRIMARY KEY,
    ticker_a VARCHAR(20) NOT NULL,
    ticker_b VARCHAR(20) NOT NULL,
    exchange_a VARCHAR(10) NOT NULL,
    exchange_b VARCHAR(10) NOT NULL,
    language VARCHAR(5) DEFAULT 'en',
    comparison_data JSONB,
    verdict VARCHAR(20),
    conviction VARCHAR(20),
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(ticker_a, ticker_b, exchange_a, exchange_b, language)
);

-- User Comparison Access (tracks which comparisons user has viewed)
CREATE TABLE user_comparisons (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    comparison_cache_id INTEGER REFERENCES comparison_cache(id),
    first_viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 11. Infrastructure & Capacity

### 11.1 Current Infrastructure (Render)

| Component | Plan | Specs | Cost |
|-----------|------|-------|------|
| **API Server** | Starter | 512MB RAM, 0.5 CPU, 2 Gunicorn workers | $7/mo |
| **Database** | Basic 256MB | PostgreSQL 15, ~20 connections | $6/mo |
| **Frontend** | Static | CDN-served static files | Free |
| **Cron Jobs** | Included | 5 scheduled jobs | Included |
| **Total** | - | - | ~$13/mo + Claude API |

### 11.2 Rate Limits

| Endpoint | Limit | Purpose |
|----------|-------|---------|
| Register | 3/minute | Prevent spam signups |
| Login | 5/minute | Prevent brute force |
| Resend Verification | 3/minute | Prevent abuse |
| Forgot Password | 3/minute | Prevent abuse |
| Reset Password | 5/minute | Prevent brute force |
| Report Generation | 10/hour | Protect Claude API costs |
| Comparison | 10/hour | Protect Claude API costs |

### 10.3 Capacity Estimates

| Metric | Current Capacity |
|--------|------------------|
| Concurrent users (browsing) | ~50-100 |
| Concurrent report generations | 2-4 (worker limited) |
| Database connections | ~20 max |
| Daily active users (comfortable) | 100-200 |
| Reports per day (sustainable) | ~500 |

### 10.4 Bottlenecks (Priority Order)

1. **Claude API (Primary Bottleneck)**
   - Each report takes 15-45 seconds to generate
   - Anthropic rate limits vary by API tier
   - Cost: ~₹3-5 per report in tokens
   - Solution: Report caching reduces repeat calls

2. **Worker Count (2 workers)**
   - Only 2 requests processed simultaneously
   - Other requests queue up
   - Long report generations block workers

3. **Database Connections (~20)**
   - Sufficient for current scale
   - May need pooling at higher load

### 10.5 Scaling Path

| Trigger | Upgrade | Cost | Benefit |
|---------|---------|------|---------|
| >100 concurrent users | API → Standard | $25/mo | 2GB RAM, 1 CPU, 4 workers |
| >500 concurrent users | API → Pro | $85/mo | 4GB RAM, 2 CPU, 8 workers |
| DB connection limits | DB → Basic 1GB | $15/mo | More connections, storage |
| High Claude API costs | Batch processing | - | Queue reports, process off-peak |
| Global users | Multi-region | Variable | Add Singapore/EU regions |

### 10.6 Cost Projections

| Users/Month | Reports/Month | Claude API Cost | Infra Cost | Total |
|-------------|---------------|-----------------|------------|-------|
| 100 | 500 | ~₹2,000 | ~₹1,100 | ~₹3,100 |
| 500 | 2,500 | ~₹10,000 | ~₹2,000 | ~₹12,000 |
| 1,000 | 5,000 | ~₹20,000 | ~₹7,000 | ~₹27,000 |

*Note: Claude API is the dominant cost factor. Report caching significantly reduces actual API calls.*

---

## 11. Design System

### 11.1 Brand Colors

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

### 11.2 Typography

| Style | Font | Weight | Size |
|-------|------|--------|------|
| Display | DM Serif Display | Regular | 36-48px |
| Heading | DM Sans | Bold | 24-32px |
| Body | DM Sans / Inter | Regular | 14-16px |
| Caption | Inter | Regular | 12px |

### 11.3 Component Patterns

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

## 12. Future Considerations (Not in Initial Scope)

- **Chat with AI:** Ask follow-up questions about a stock
- **Portfolio tracking:** Track holdings and performance
- **Alerts:** Price alerts, report refresh notifications
- **API access:** Enterprise tier programmatic access
- **Mobile app:** Native iOS/Android apps
- **International stocks:** US, UK, other markets

---

## 13. Success Metrics

| Metric | Target |
|--------|--------|
| User signups (Month 1) | 500 |
| Free to paid conversion | 5% |
| Reports generated/day | 100 |
| User retention (30-day) | 40% |
| Average reports/user | 5 |

---

## 14. Contact

**Product:** Permabullish
**Enterprise inquiries:** mail@mayaskara.com
**Website:** permabullish.com

---

*This document is a living specification and will be updated as the product evolves.*
