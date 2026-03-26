# Permabullish - Product Roadmap
## AI Stock Researcher

**Version:** 3.7
**Last Updated:** March 26, 2026

---

## Overview

This roadmap outlines the development phases for Permabullish AI Stock Researcher. The product is now live at **permabullish.com** with a working subscription and payment system.

---

## Phase 0: Repository Cleanup
**Status:** ✅ COMPLETE
**Completed:** January 30, 2026
**Priority:** High

### Objective
Archive existing permabullish-ai code and prepare for the pivoted product.

### Tasks

- [x] **Archive existing code**
  - Created local backup at `F:\Dev\ClaudeProjects\_archive\`
  - Removed MF-related folders: `mf-frontend/`
  - Removed PMS-related folders: `pms-backend/`, `pms-frontend/`
  - Removed old landing page: `landing/`
  - Kept: `backend/`, `frontend/`, `docs/`

- [x] **Update render.yaml**
  - Removed MF and PMS service definitions
  - Kept: API backend (`permabullish-api`), static frontend (`permabullish-web`), database
  - Added Cashfree environment variable placeholders

- [x] **Update documentation**
  - Updated README.md with new product description
  - Created PRD.md and ROADMAP.md

### Deliverables
- ✅ Clean repository with only stock research components
- ✅ Local archive of removed code at `_archive/`
- ✅ Updated render.yaml

---

## Phase 1: Core Product Enhancement
**Status:** ✅ COMPLETE
**Completed:** January 30, 2026
**Priority:** High
**Dependencies:** Phase 0

### Objective
Enhance the existing equity research generator with new features.

### 1.1 Report Caching System

- [x] Create `report_cache` table for shared reports
- [x] Modify report generation to check cache first
- [x] Add cache lookup by ticker/exchange (`GET /api/reports/cached/{ticker}`)
- [x] Display report generation date prominently on all reports
- [x] Implement freshness logic:
  - First-time viewer + >15 days old → auto-regenerate fresh report
  - Returning viewer + >15 days old → show cached report with regenerate option
- [x] Add "Regenerate Report" button for reports >15 days old (consumes quota)

### 1.2 User Dashboard Enhancement

- [x] Design new dashboard layout with:
  - Current price display
  - AI recommended price
  - User's target price (editable)
  - Report link/status
- [x] Created tabs for Reports and Watchlist views
- [x] Add user target price input/storage (`PUT /api/user/target-price`)
- [x] Created dashboard API endpoints

### 1.3 Watchlist Feature

- [x] Create `watchlist` table
- [x] Add watchlist API endpoints (CRUD):
  - `GET /api/watchlist`
  - `POST /api/watchlist`
  - `DELETE /api/watchlist/{ticker}`
  - `GET /api/watchlist/check/{ticker}`
- [x] Build watchlist UI component (toggle button on generate page)
- [x] Show "No report" indicator for stocks without reports
- [x] Add "Generate Report" action from watchlist

### 1.4 Report History Enhancement

- [x] Create `user_reports` table linking users to cached reports
- [x] Build report history page (dashboard Reports tab)
- [x] Add visual indicators:
  - "Outdated" badge (>15 days)
  - Days old indicator
- [x] Add quick actions: View, Regenerate

### 1.5 Bug Fixes & Infrastructure

- [x] Fixed CORS configuration (always include production URLs)
- [x] Fixed PostgreSQL compatibility (dict vs tuple row access)
- [x] Added database initialization on startup (`init_database()`)
- [x] Added admin endpoint for usage reset (`/api/admin/reset-usage`)

### Deliverables
- ✅ Report caching with freshness tracking
- ✅ Enhanced dashboard with tabs for Reports/Watchlist
- ✅ Working watchlist feature
- ✅ Complete report history with freshness indicators
- ✅ User target price feature

---

## Phase 2: Subscription System
**Status:** ✅ COMPLETE
**Completed:** January 31, 2026
**Priority:** High
**Dependencies:** Phase 1

### Objective
Implement tiered subscription system with usage limits.

### 2.1 Subscription Tiers

- [x] Define tier limits in config:
  ```python
  SUBSCRIPTION_TIERS = {
      'free': {'reports_per_month': 3, 'price_monthly': 0},
      'basic': {'reports_per_month': 10, 'price_monthly': 199, 'price_6months': 999, 'price_yearly': 1799},
      'pro': {'reports_per_month': 50, 'price_monthly': 499, 'price_6months': 2499, 'price_yearly': 4499},
      'enterprise': {'reports_per_month': float('inf')}
  }
  ```
- [x] Create `subscriptions` table
- [x] Implement subscription status checking
- [x] Add subscription expiry handling

### 2.2 Usage Tracking

- [x] Enhance `usage` table for monthly tracking
- [x] Reset usage on 1st of each month (paid tiers)
- [x] Implement quota enforcement on report generation
- [x] Create usage display component
- [x] Add "X reports remaining" indicator

### 2.3 Pricing Page

- [x] Design pricing page with tier comparison (`frontend/pricing.html`)
- [x] Show: Free (5 reports), Pro (100/mo), Enterprise (contact us)
- [x] Add payment period options: 1 month, 6 months, 12 months
- [x] Display savings percentages for longer periods
- [x] "Contact us" for Enterprise tier
- [x] Simplified to Free + Pro + Enterprise (Basic retired Feb 2026)

### 2.4 Upgrade Flow

- [x] Create upgrade prompts when quota exhausted
- [x] Build subscription selection UI
- [x] Implement subscription API endpoints
- [x] Add subscription status to user profile

### Deliverables
- ✅ Working tier system with limits
- ✅ Usage tracking and display
- ✅ Pricing page with all plans
- ✅ Upgrade flow UI

---

## Phase 3: Payment Integration
**Status:** ✅ COMPLETE
**Completed:** January 31, 2026
**Priority:** High
**Dependencies:** Phase 2

### Objective
Integrate Cashfree for subscription payments.

### 3.1 Cashfree Setup

- [x] Created Cashfree merchant account
- [x] Obtained API credentials (App ID, Secret Key)
- [x] **Used Payment Forms instead of Payment Gateway** (due to domain whitelisting requirements)
- [x] Created payment forms for Pro plan (Basic retired Feb 2026):
  - Pro: Monthly, 6-Months, Yearly
- [x] Configured webhook endpoints

### 3.2 Payment Flow

- [x] Payment forms handle checkout (no API integration needed)
- [x] Users redirected to Cashfree payment form
- [x] Handle Cashfree webhooks (`POST /api/webhooks/payment-form`):
  - `payment_form.payment.success` - activates subscription
  - Matches customer email to user account
  - Determines tier/period from payment amount
- [x] Update subscription on successful payment

### 3.3 Payment UI

- [x] Pricing page redirects to appropriate payment form
- [x] Shows email reminder before redirect
- [x] Payment success handled by Cashfree redirect

### 3.4 Subscription Management

- [x] Created subscription management page (`frontend/subscription.html`)
- [x] Shows current plan, expiry date, usage statistics
- [x] Upgrade options for higher tiers/longer periods
- [x] Period upgrades allowed (monthly → 6 months → yearly)

### 3.5 Enterprise User Management

- [x] Admin endpoints for creating enterprise users:
  - `POST /api/admin/enterprise/users` - Create enterprise user
  - `GET /api/admin/enterprise/users` - List enterprise users
  - `PUT /api/admin/enterprise/users/{user_id}` - Update enterprise user
- [x] Documentation in `docs/ADMIN_GUIDE.md`

### Deliverables
- ✅ Working Cashfree Payment Forms integration
- ✅ Complete payment flow
- ✅ Subscription management UI
- ✅ Webhook handling
- ✅ Enterprise user management

---

## Phase 3.5: Production Launch
**Status:** ✅ COMPLETE
**Completed:** January 31, 2026
**Priority:** High

### Objective
Launch the product on custom domain with production-ready features.

### 3.5.1 Custom Domain Setup

- [x] Configured permabullish.com on Namecheap DNS
- [x] Set up Render hosting for frontend and API
- [x] Configured SSL certificates (Let's Encrypt)
- [x] Added CAA records for certificate issuance
- [x] Updated environment variables for production URLs

### 3.5.2 Social Sharing (WhatsApp Virality)

- [x] Created share card generator (`backend/share_card.py`)
- [x] Generates 1200x630 PNG images with Pillow
- [x] Open Graph image endpoint (`GET /api/reports/{id}/og-image`)
- [x] Share page with OG meta tags (`GET /api/reports/{id}/share`)
- [x] Updated WhatsApp share to use rich preview URLs
- [x] Share card includes:
  - Company name and ticker
  - Recommendation badge (color-coded)
  - AI Target Price
  - Potential Upside percentage
  - Current Price
  - Permabullish branding

### 3.5.3 UX Improvements

- [x] Added loading skeletons to dashboard stats cards
- [x] Eliminated visual jitter on page load
- [x] Smooth transitions when data loads

### Deliverables
- ✅ Live at permabullish.com
- ✅ Social sharing with rich previews
- ✅ Polished UX with loading states

---

## Phase 3.6: Post-Launch Improvements
**Status:** ✅ COMPLETE
**Completed:** January 31, 2026
**Priority:** High

### Objective
Polish and enhance the live product based on initial usage.

### 3.6.1 Email System (Resend Integration)

- [x] **Welcome Email** - Sent on signup (email/password and Google OAuth)
  - Introduces platform features
  - Includes 3 featured sample reports (INFY, SWIGGY, DIXON)
  - Configurable featured tickers in `config.py`
- [x] **Purchase Confirmation Email** - Sent on subscription activation
  - Plan details, expiry date, reports per month
  - Triggered from verify endpoint and webhooks
- [x] **Re-engagement Email System (Enhanced)**
  - **16 rotating templates + weekly digest** (expanded from 5)
  - Template categories:
    - 5 generic templates for retail investors
    - 5 broker-focused templates targeting brokers, sub-brokers, APs
    - 2 Hindi language templates (हिंदी)
    - 2 Gujarati language templates (ગુજરાતી)
    - 2 Kannada language templates (ಕನ್ನಡ)
    - 1 weekly digest template
  - Days 1-16: Daily emails (if inactive 7+ days)
  - Days 17-180: Weekly emails (if inactive 7+ days)
  - Cron script: `scripts/send_reengagement_emails.py`
  - IST timezone support
  - Rate limiting: 0.6s delay between sends (Resend API: 2 req/sec)
- [x] **External Contacts System**
  - Import CSV email lists: `scripts/import_external_contacts.py`
  - Same template rotation as registered users
  - `external_contacts` table with tracking columns
  - Supports promotional campaigns to external lists
- [x] **Bounced Email Cleanup**
  - Fetches email delivery status from Resend API
  - Marks bounced/failed contacts as inactive
  - Script: `scripts/cleanup_bounced_emails.py`
- [x] Database tracking columns: `last_activity_at`, `welcome_email_sent`, `last_reengagement_email_at`, `reengagement_email_count`

### 3.6.2 AI Report Enhancements

- [x] **Fiscal Quarter Grounding**
  - Reports now include current date context
  - Indian fiscal year awareness (Apr-Mar, Q1-Q4)
  - Latest results quarter labeling (e.g., "Q2 FY26 (Jul-Sep 2025)")
  - Prevents AI from referencing future dates

### 3.6.3 Search & Discovery

- [x] **Stock Search by Company Name**
  - Fixed: Search now works with company names, not just tickers
  - Merged Nifty 500 names with expanded NSE list
  - Example: "Infosys" now finds INFY
- [x] **"3000+ Stocks Covered" Badge**
  - Added prominently on login page below tagline

### 3.6.4 UX & Legal

- [x] **Disclaimer Footer on All Pages**
  - "Not financial advice" disclaimer
  - Contact Us mailto link (mail@mayaskara.com)
  - Added to: index, dashboard, generate, pricing, subscription, checkout, payment-status, report
- [x] **Share Message Updates**
  - "NOT FINANCIAL ADVICE" included in WhatsApp/Twitter shares
  - Consistent share URL format (always uses api.permabullish.com)

### 3.6.5 Bug Fixes

- [x] **Cached Report Regeneration**
  - Fixed: "Generate Fresh Report" button now properly regenerates
  - `force_regenerate` flag correctly sent to backend
- [x] **Share URL Consistency**
  - Fixed: Share URLs always use production domain regardless of access method

### 3.6.6 Email Deliverability ⬅️ IN PROGRESS

**Goal:** Improve inbox placement, especially for Gmail users.

#### Completed ✅
- [x] **DNS Authentication**
  - SPF record configured
  - DKIM record configured (Resend)
  - DMARC record configured (`p=none`)
- [x] **Unsubscribe Compliance**
  - Unsubscribe link in all email footers
  - `List-Unsubscribe` and `List-Unsubscribe-Post` headers
  - `/api/unsubscribe` endpoint
  - `frontend/unsubscribe.html` page
- [x] **Domain Warm-up**
  - Started at 100 emails/batch (300/day total)
  - Increased to 200 emails/batch (600/day total)
  - Batched sending at 9 AM, 2 PM, 6 PM IST
  - Configurable via `--batch-size` flag
- [x] **Bounce Cleanup Automation**
  - Daily cron at 8:30 PM IST (3 PM UTC)
  - Runs ~2 hours after last promo batch
  - Marks bounced/failed contacts as inactive

#### Week 2 (Feb 13, 2026)
- [x] **Check Google Postmaster Tools** ✅
  - Domain verified
  - Spam rate: 0%
  - Authentication: passing
- [x] **Increase sending limits**
  - Increased to 200/batch (600/day)

#### Week 3-4 (Feb 20-27, 2026)
- [ ] **Upgrade DMARC policy**
  - Change from `p=none` to `p=quarantine`
  - Monitor for delivery issues
- [ ] **Increase sending limits**
  - Scale to 400/batch, then remove limits

#### Future (After DMARC Enforcing)
- [ ] **BIMI Setup (Brand Logo in Gmail)**
  - Requires DMARC `p=quarantine` or `p=reject`
  - Create SVG logo in required format
  - Optional: VMC certificate (~$1,500/year)
  - Shows brand logo next to emails in Gmail

#### Content Improvements ✅
- [x] Changed from address from `noreply@` to `hello@permabullish.com`
- [x] Added plain text version to all emails (multipart via Resend `text` param)
- [x] Reduced links per email (report cards non-clickable, removed secondary CTAs)
- [x] Removed spam trigger words ("Free" removed from 5 CTA buttons)

### Deliverables
- ✅ Complete email automation system
- ✅ Fiscally-grounded AI reports
- ✅ Improved stock search
- ✅ Legal compliance (disclaimers)
- ✅ Bug fixes for regeneration and sharing

### Environment Variables (New)
- `RESEND_API_KEY` - Email service API key

### Pending (Email System)
- [x] DNS verification for permabullish.com (SPF, DKIM) ✅
- [x] Set up cron job for re-engagement emails on Render ✅

---

## Phase 4: Data Enhancement
**Status:** ✅ COMPLETE
**Priority:** High
**Dependencies:** Phase 1

### Objective
Improve stock data quality and coverage.

### 4.1 Stock Coverage Expansion ✅

- [x] Expanded to 2000+ NSE stocks (`data/nse_eq_stocks.json`)
- [x] Merged with Nifty 500 company names for better search
- [x] Update stock search to work with company names (not just tickers)
- [x] Add newer listings (Swiggy, Nykaa, etc.)

### 4.2 Fundamentals Data Scraper ✅

- [x] Build fundamentals fetcher (`scripts/fundamentals_sync.py`)
- [x] Extract key data: P/E, ROE, ROCE, quarterly results, shareholding
- [x] Create `stock_fundamentals` table schema
- [x] Handle rate limiting (0.5s delay between requests)
- [x] Support single-stock and batch sync modes

### 4.3 Report Generator Integration ✅

- [x] Modified `yahoo_finance.py` to merge cached Screener data
- [x] Added `get_cached_fundamentals()` to database.py
- [x] Updated AI prompt to analyze shareholding TRENDS (buying/selling)
- [x] Added shareholding insight section to HTML reports
- [x] Integrated Screener pros/cons into AI analysis

### 4.4 Initial Data Sync ✅ COMPLETE

- [x] Database operations module (`fundamentals_db.py`)
- [x] Run sync for all 2000+ stocks
- [x] Data populated in production database

### 4.5 Infrastructure Upgrade ✅

- [x] **Upgrade to paid Render tier** ✅
  - Cron jobs enabled
  - Better performance and uptime
  - No cold starts on API
- [x] Set up cron jobs ✅
  - Re-engagement emails: daily at 10 AM IST
  - Expiry reminder emails: daily at 10:30 AM IST
  - Fundamentals refresh: 1st of month
  - Daily/weekly usage reports
- [ ] Add on-demand refresh for stale data (>45 days)

### Deliverables
- ✅ 2000+ NSE stocks searchable
- ✅ Fundamentals sync infrastructure
- ✅ Report generator integration (shareholding trends, pros/cons)
- ✅ Initial data population complete
- ✅ Cron jobs configured in render.yaml

---

## Phase 5: Pricing Analysis
**Status:** ✅ COMPLETE
**Priority:** Medium
**Dependencies:** Phase 2, Phase 3

### Objective
Determine optimal pricing based on token consumption and costs.

### 5.1 Token Usage Analysis

- [x] Added token tracking columns to database (`input_tokens`, `output_tokens`)
- [ ] Implement logging of token usage per report generation
- [ ] Track: input tokens, output tokens, total cost
- [ ] Calculate average cost per report
- [ ] Analyze cost variance by stock complexity

### 5.2 Cost Modeling

- [ ] Calculate infrastructure costs:
  - Render hosting
  - Database storage
  - API calls (Claude, Yahoo Finance)
- [ ] Model costs per user per tier
- [ ] Determine break-even points

### 5.3 Pricing Strategy

- [x] Research competitor pricing
- [x] Simplified to Pro-only paid tier (Basic retired Feb 2026)
- [x] New Pro pricing: ₹749/mo, ₹2,999/6mo, ₹4,999/yr
- [x] Struck prices: ₹1,999, ₹11,999, ₹23,999

### Deliverables
- Token usage analytics
- Cost model spreadsheet
- Pricing validation/adjustment

---

## Phase 6: Landing Page & Marketing
**Status:** ❌ DROPPED
**Reason:** Current flow drops users directly into product, which works well

*Note: May revisit post-launch if conversion optimization is needed.*

---

## Phase 6: Mobile UX Optimization
**Status:** Pending
**Priority:** Medium

### Objective
Ensure perfect mobile experience across all screens.

### 6.1 Mobile Audit

- [ ] Report screen - fix AI target banner blocking elements
- [ ] Report screen - fix text cutoff in cards
- [ ] Watchlist table - smaller icons and text
- [ ] Pricing screen - optimize for mobile
- [ ] Dashboard - further mobile optimization

### Deliverables
- Fully responsive design on all screens
- No overlapping/blocking elements
- Proper text sizing and spacing

---

## Phase 7: Multi-Language Support
**Status:** ✅ COMPLETE
**Completed:** February 2, 2026
**Priority:** Low

### Objective
Add Hindi, Gujarati, and Kannada language support for reports.

### 7.1 Language Selection ✅

- [x] Add language toggle to report generation page
- [x] Options: English (EN), Hindi (हिंदी), Gujarati (ગુજરાતી), Kannada (ಕನ್ನಡ)
- [x] Mobile-friendly toggle buttons
- [x] Each language cached separately per stock

### 7.2 Report Translation ✅

- [x] Modified AI prompt with language-specific instructions
- [x] Technical/financial terms kept in English (P/E, ROE, etc.)
- [x] Company names in English
- [x] Added Noto Sans Devanagari, Gujarati, and Kannada fonts

### 7.3 UI Integration ✅

- [x] Language badge shown on report history (dashboard)
- [x] Different colored badges (orange for Hindi, green for Gujarati, purple for Kannada)
- [x] Language passed through API to backend

### Deliverables
- ✅ Language selection UI on generate page
- ✅ Reports generated in Hindi, Gujarati, and Kannada
- ✅ Proper font rendering with Google Fonts
- ✅ Language indicator in report history

---

## Phase 7.6: Stock Comparison Tool
**Status:** ✅ COMPLETE
**Completed:** February 2, 2026
**Priority:** High

### Objective
Add a stock comparison feature where users can compare two stocks side-by-side with AI-powered verdict.

### 7.6.1 Backend - Comparison API ✅

- [x] Added `CompareRequest` Pydantic model
- [x] Created `POST /api/reports/compare` endpoint
- [x] Fetches stock data for both stocks in parallel
- [x] Checks for cached comparisons by ticker pair + language
- [x] Added `generate_comparison_analysis()` to `report_generator.py`
- [x] AI compares stocks across: Valuation, Growth, Quality, Risk
- [x] Returns verdict (STOCK_A, STOCK_B, or EITHER) with conviction level
- [x] Deducts 1 report credit per comparison

### 7.6.2 Backend - Comparison Caching ✅

- [x] Created `comparison_cache` table for shared comparisons
- [x] Created `user_comparisons` table linking users to comparisons
- [x] Added `save_comparison()` and `get_cached_comparison()` functions
- [x] Added `GET /api/comparisons` endpoint for user history
- [x] Added `GET /api/comparisons/{id}` endpoint for specific comparison

### 7.6.3 Backend - Social Sharing ✅

- [x] Added `generate_comparison_share_card()` to `share_card.py`
- [x] Creates 1200x630 PNG with verdict, tickers, and conviction
- [x] Dynamic ticker badge positioning (handles long ticker names)
- [x] Added `GET /api/comparisons/{id}/og-image` endpoint
- [x] Added `GET /api/comparisons/{id}/share` page with OG meta tags

### 7.6.4 Frontend - compare.html ✅

- [x] Created comparison page with dual stock search
- [x] Language selector (EN, Hindi, Gujarati)
- [x] "Compare Now" button with loading state
- [x] Verdict banner with trophy icon and conviction badge
- [x] Metrics comparison table with winner highlighting
- [x] Sticky bottom share bar (WhatsApp, Telegram, X, Copy)
- [x] Mobile responsive layout

### 7.6.5 Dashboard Integration ✅

- [x] Added "Comparisons" tab between Reports and Watchlist
- [x] Shows comparison history with ticker pairs and verdicts
- [x] Clicking comparison loads cached result (via `?id=` parameter)
- [x] Added `loadCachedComparison()` function

### 7.6.6 UX Improvements ✅

- [x] Wake Lock API prevents screen sleep during generation
- [x] Fixed WhatsApp/Telegram share links (were opening blank)
- [x] Shortened comparison page (removed Bull/Bear Cases, "Who Should Buy")
- [x] Navigation links added from dashboard and generate pages

### Deliverables
- ✅ Full stock comparison feature
- ✅ Multi-language support (EN, Hindi, Gujarati)
- ✅ Comparison caching and history
- ✅ Social sharing with OG images
- ✅ Mobile-optimized UI

### New Files
- `frontend/compare.html` - Comparison page UI

### Modified Files
- `backend/main.py` - Comparison endpoints
- `backend/report_generator.py` - AI comparison function
- `backend/database.py` - Comparison caching functions
- `backend/share_card.py` - Comparison OG image generation
- `frontend/dashboard.html` - Comparisons tab
- `frontend/generate.html` - Wake Lock API, compare link

---

## Phase 7.5: Security & Best Practices
**Status:** 🔄 IN PROGRESS
**Priority:** High

### 7.5.1 Security Hardening

- [x] **Disable Swagger in Production** ✅
  - Hidden `/api/docs`, `/api/redoc`, `/openapi.json` in production
  - Prevents API structure exposure

- [x] **Rate Limiting** ✅
  - Register: 3/minute
  - Login: 5/minute
  - Report generation: 10/hour
  - Uses slowapi

- [ ] **Input Validation**
  - Validate ticker symbols before Claude API calls
  - Sanitize all user inputs

### 7.5.2 Monitoring & Observability

- [x] **Error Tracking (Sentry)** ✅
  - Production errors captured automatically
  - Stack traces and request context
  - Test endpoint: `/api/sentry-test`

- [ ] **Health Check Improvements**
  - Add database connectivity check to `/api/health`
  - Add external API status (Claude, Resend)
  - Consider external uptime monitoring (UptimeRobot - free)

- [ ] **Structured Logging**
  - JSON logging for easier parsing
  - Log report generation metrics

### 7.5.3 Infrastructure

- [x] **Cron Jobs Setup** ✅
  - Re-engagement emails: daily 10 AM IST
  - Expiry reminder emails: daily 10:30 AM IST
  - Fundamentals sync: 1st of month
  - Daily/weekly usage reports

- [ ] **Backup Strategy**
  - Verify Render PostgreSQL auto-backups
  - Consider periodic export to external storage

- [ ] **CI/CD Pipeline** (Nice to have)
  - GitHub Actions for lint/test on PR
  - Auto-deploy to staging on merge

### 7.5.4 Analytics

- [x] **Google Analytics (GA4)** ✅
  - Tracking on all 8 frontend pages
  - Custom events: registration, login, report generation, shares, search, watchlist, purchases
  - User properties: tier, account type, reports count
  - E-commerce tracking for subscription purchases
  - Measurement ID: G-75Y271369Q

- [ ] **Admin Stats API**
  - `/api/admin/stats` endpoint
  - User counts, report counts, subscription breakdown, MRR

---

## Phase 7.8: Report Quality Enhancements
**Status:** 🔄 IN PROGRESS
**Priority:** High
**Started:** February 3, 2026

### Objective
Improve the depth and quality of AI-generated reports with charts, management analysis, and sector-specific insights.

### 7.8.1 Stock Price Charts ✅ COMPLETE

- [x] **Chart Integration**
  - Interactive price chart on report page using Lightweight Charts v4.1.0
  - Timeframes: 1M, 3M, 6M, 1Y (default), 5Y
  - 50-day and 200-day SMA overlay (dashed lines)
  - Area chart with orange gradient fill
  - Dark theme matching site design

- [x] **Technical Signals**
  - 52-week high/low displayed in chart footer
  - MA50 and MA200 values shown
  - Period return percentage (green/red)

- [x] **Implementation**
  - Used Lightweight Charts (TradingView open-source) + Yahoo Finance data
  - Backend: `GET /api/stocks/{symbol}/chart` endpoint
  - Data: `yahoo_finance.py` → `fetch_chart_data()` with MA calculation
  - Chart injected via iframe in report page, responsive with ResizeObserver

### 7.8.2 Management Quality Assessment

- [ ] **Data Points to Include**
  - Promoter background and track record
  - Promoter holding % and pledge status
  - Related party transactions
  - Capital allocation history (dividends, buybacks, acquisitions)
  - Board composition and independence
  - Auditor changes (red flag indicator)
  - Corporate governance score

- [ ] **AI Analysis**
  - Add management quality section to report prompt
  - Rate management on scale (Excellent/Good/Average/Poor)
  - Highlight any governance red flags

- [ ] **Data Sources**
  - Screener.in (promoter holding, pledges)
  - BSE/NSE announcements (governance disclosures)
  - Manual curation for top 200 stocks initially

### 7.8.3 Sector-Specific Analysis Templates

- [ ] **Banking & NBFC**
  - NPA ratios (Gross NPA, Net NPA)
  - NIM (Net Interest Margin)
  - CASA ratio
  - Capital adequacy (CAR)
  - Credit cost trends
  - Loan book composition

- [ ] **IT Services**
  - Revenue by geography
  - Deal wins / TCV (Total Contract Value)
  - Attrition rate
  - Utilization rate
  - Top client concentration

- [ ] **Pharmaceuticals**
  - Domestic vs Export split
  - US FDA observations / warning letters
  - ANDA pipeline
  - API vs Formulations mix
  - R&D spend as % of revenue

- [ ] **FMCG / Consumer**
  - Volume growth vs Value growth
  - Rural vs Urban mix
  - Distribution reach
  - Brand strength / market share
  - Raw material cost trends

- [ ] **Auto & Auto Ancillary**
  - Production / sales volumes
  - EV transition readiness
  - Export %
  - OEM vs Aftermarket mix
  - Capacity utilization

- [ ] **Implementation**
  - Detect sector from stock metadata
  - Load sector-specific prompt additions
  - Include relevant metrics in data fetch
  - Display sector-specific section in report

### Deliverables
- [ ] Interactive price charts on reports
- [ ] Management quality section in reports
- [ ] Sector-specific analysis for top 5 sectors
- [ ] Enhanced AI prompts for deeper analysis

---

## Phase 7.9: Email/Password Authentication
**Status:** ✅ COMPLETE
**Completed:** February 7, 2026
**Priority:** High

### Objective
Add email/password authentication alongside Google OAuth, with email verification and password reset flows.

### 7.9.1 Backend - Auth Infrastructure ✅

- [x] Added `email_verified` column to users table (with migrations for both Postgres and SQLite)
- [x] Added `password_hash` and `auth_provider` columns
- [x] Created purpose-specific JWT tokens:
  - `create_verification_token()` - 24-hour expiry, purpose="email_verify"
  - `create_password_reset_token()` - 1-hour expiry, purpose="password_reset"
  - `decode_purpose_token()` - validates purpose and expiry
- [x] Updated `register_user()` to send verification email instead of welcome email
- [x] Updated `authenticate_user()` to check `email_verified` before login
- [x] Google OAuth users auto-verified (`email_verified = TRUE`)

### 7.9.2 Backend - New API Endpoints ✅

- [x] `POST /api/auth/register` - Returns verification prompt (no auto-login)
- [x] `GET /api/auth/verify-email?token=` - Validates token, marks verified, redirects to frontend
- [x] `POST /api/auth/resend-verification` - Rate limited 3/min, never reveals email existence
- [x] `POST /api/auth/forgot-password` - Rate limited 3/min, skips Google-only users
- [x] `POST /api/auth/reset-password` - Rate limited 5/min, validates token, updates password

### 7.9.3 Backend - Email Templates ✅

- [x] `send_verification_email()` - Verification link with spam folder warning
- [x] `send_password_reset_email()` - Reset link with 1-hour expiry warning
- [x] Both reuse existing email styling (`get_email_styles()`, `get_footer()`)

### 7.9.4 Frontend - Login Page Update ✅

- [x] Added email/password sign-in form below Google button
- [x] Sign-up form with toggle (sign-in ↔ sign-up)
- [x] "Forgot password?" link
- [x] Error/success message handling
- [x] On registration: redirects to verify-email.html

### 7.9.5 Frontend - New Pages ✅

- [x] `verify-email.html` - Three modes:
  - Pending: "Check your email" with resend button
  - Success: "Email verified!" with sign-in link
  - Error: Expired/invalid token with resend option
- [x] `reset-password.html` - Two modes:
  - Request: Email input → sends reset link
  - Reset: New password form → updates password

### 7.9.6 Account Linking ✅

- [x] Email/password user → later signs in with Google (same email) → accounts linked
- [x] Google-only user → tries email/password register → shown "Try signing in with Google"
- [x] Users with both methods can use either to sign in

### Deliverables
- ✅ Complete email/password registration with email verification
- ✅ Password reset flow (forgot → email → reset)
- ✅ Account linking between Google OAuth and email/password
- ✅ Rate-limited auth endpoints
- ✅ Secure token-based verification (no email existence leaks)

### New Files
- `frontend/verify-email.html` - Email verification page
- `frontend/reset-password.html` - Password reset page

### Modified Files
- `backend/database.py` - email_verified column, migrations, helpers
- `backend/auth.py` - Verification/reset token helpers, updated register/authenticate
- `backend/email_service.py` - Verification and reset email templates
- `backend/main.py` - New auth endpoints, updated register flow
- `frontend/index.html` - Email/password sign-in/sign-up UI

---

## Phase 7.95: Shared Report Content Gate (Conversion Optimization)
**Status:** ✅ COMPLETE
**Completed:** February 16, 2026
**Priority:** High

### Objective
Gate shared report content for unauthenticated users to drive sign-ups. Show the intro/thesis readable, then blur everything from Bull/Bear Case onward with a sign-up CTA overlay. After signing in, the user lands back on the same report.

### 7.95.1 Content Gate ✅

- [x] **Blur + CTA overlay** injected into report iframe for guests
  - Finds `.thesis-grid` (Bull/Bear case container) in iframe DOM
  - Applies CSS `blur(8px)` to thesis-grid, all subsequent sections, and footer
  - Gradient fade-to-white overlay with CTA card before blurred content
  - CTA includes: "Continue Reading" heading, Google sign-in button, email signup link, "No credit card required" note
- [x] **Replaced guest nudge banner** — removed the dismissible top banner in favour of inline content gate (higher conversion surface)
- [x] **GA4 tracking events**
  - `content_gate_shown` — fired when gate overlay is injected (ticker, report_id)
  - `content_gate_cta_clicked` — fired on Google or email CTA click (cta_type)

### 7.95.2 Return-to-Report after Sign-In ✅

- [x] **Google OAuth flow**
  - `signInWithGoogle()` in report.html passes `return_to=/report.html?id=X` to backend
  - Backend `google_login` stores `return_to` in session (validated: must start with `/`)
  - Backend `google_callback` redirects to `{FRONTEND_URL}{return_to}?token=X` instead of dashboard
  - report.html `handleOAuthReturn()` IIFE detects `?token=` param, stores in localStorage, cleans URL
- [x] **Email auth flow**
  - `gateSignUpWithEmail()` stores `window.location.href` in `localStorage.return_to`
  - index.html checks `localStorage.return_to` after successful login/register
  - Redirects to stored URL instead of dashboard.html, then removes key
  - Also works when user clicks Google sign-in on index.html (passes return_to to backend)
- [x] **Security: open redirect prevention**
  - Backend validates `return_to` starts with `/` (relative path only)
  - No external URLs accepted

### What's NOT Affected
- `/api/reports/{id}/view` endpoint (Telegram/Instagram direct rendering) — unchanged
- Logged-in users — no blur, no CTA, full report as before
- Report generation flow — unchanged
- Normal dashboard redirect — still works when no `return_to` is set

### Deliverables
- ✅ Content gate with blur + CTA overlay on shared reports for guests
- ✅ Return-to-report flow for both Google OAuth and email auth
- ✅ GA4 conversion tracking events
- ✅ No breaking changes to existing flows

### Modified Files
- `frontend/report.html` — Content gate, OAuth return handling, removed guest nudge
- `frontend/index.html` — return_to redirect after login/register/OAuth
- `backend/main.py` — return_to param in Google OAuth login/callback

---

## Phase 8: US Market Expansion
**Status:** ✅ COMPLETE
**Completed:** March 2026
**Priority:** High

### Objective
Expand Permabullish to cover US stocks (NYSE, NASDAQ) alongside Indian stocks. Delivered as a **unified codebase** — no subdomain, no separate deployment. One product, one search, both markets.

### 8.1 Architecture Decision ✅
- **Unified codebase** chosen over subdomain fork
- Single search returns both Indian + US results
- Exchange detection via `config.is_us_exchange()` / `config.is_indian_exchange()`
- No additional Render service or DNS changes needed

### 8.2 Data Sources ✅
- [x] **Yahoo Finance** — prices (works natively for US tickers, no suffix)
- [x] **Financial Modeling Prep (FMP)** — fundamentals (free 250/day tier)
  - `backend/data_sources/fmp.py` — FMP API client
  - `FMP_API_KEY` environment variable
- [x] **Finnhub** — additional US data fallback (`backend/data_sources/finnhub.py`)
- [x] **Twelve Data** — additional US data fallback (`backend/data_sources/twelve_data.py`)

### 8.3 Implementation ✅

- [x] **Stock List** — `backend/data/sp500_stocks.json` (503 stocks, NYSE + NASDAQ)
- [x] **Ticker Resolution** — US tickers: no suffix; Indian: `.NS` / `.BO`
- [x] **Provider Selection** — Groww/Tickertape/Screener skipped for US stocks
- [x] **AI Prompt Branching** — US gets: calendar FY (Jan-Dec), institutional ownership instead of promoter/FII/DII, ROIC instead of ROCE, $ instead of ₹
- [x] **Currency** — `currency_symbol` var in HTML; `format_us_market_cap()` for $T/$B/$M
- [x] **All languages supported** for US stocks (Hindi/Gujarati/Kannada reports for US stocks)
- [x] **Fundamentals Sync** — `scripts/us_fundamentals_sync.py`
- [x] **FMP migration** — Upgraded from deprecated FMP v3 to stable endpoints (Mar 2026)

### Deliverables
- ✅ 503 S&P 500 stocks searchable alongside 3,000+ Indian stocks
- ✅ US stock reports with correct currency, FY context, ownership breakdown
- ✅ Multi-language support for US stocks
- ✅ No new infrastructure — same Render services

### Note on Subdomain & Payments
- `us.permabullish.com` subdomain deferred — unified approach sufficient for now
- Stripe (USD payments) deferred — US audience not targeted for paid tier yet

---

## Phase 9: Performance Optimization
**Status:** 🔄 IN PROGRESS
**Priority:** Medium

### Objective
Improve application performance, reduce latency, and handle scale efficiently.

### 9.1 Quick Wins (Low Effort, High Impact)

- [x] **Chart Data Caching** ✅
  - In-memory TTL cache for chart endpoint responses
  - Cache key: `{ticker}:{exchange}:{period}`, TTL: 5 minutes
  - Eliminates repeated Yahoo Finance API calls and MA recalculations
  - Auto-evicts stale entries when cache exceeds 500 entries
  - Estimated reduction: ~90% of chart API calls

- [x] **Database Indexes** ✅
  - `report_cache(ticker, exchange)` — report lookups on every generation
  - `user_reports(user_id)` — dashboard report history
  - `watchlist(user_id)` — watchlist listing
  - Added to both Postgres and SQLite init, created on next deploy/restart

- [x] **GZip Compression (API)** ✅
  - `GZipMiddleware` added to FastAPI (minimum_size=500 bytes)
  - ~70% reduction in API response transfer size

- [x] **Static Asset Cache Headers** ✅
  - Increased `max-age` from 3600 (1 hour) to 86400 (1 day) in `render.yaml`

### 9.2 Medium Effort (Half-Day Each)

- [ ] **Parallel Provider Fallback**
  - Currently: Yahoo → Groww → Tickertape → Alpha Vantage **sequentially** (10-15s timeout each)
  - Fix: Try all available providers in parallel via ThreadPoolExecutor
  - Use first successful response, cancel the rest
  - Worst-case latency: 15s (one timeout) instead of 45s+ (three timeouts)

- [ ] **In-Memory Report Cache (LRU)**
  - TTLCache for recently viewed reports (last 100-200 reports)
  - Avoids PostgreSQL round-trip for repeat views within same session
  - Especially helpful for shared report links (viral traffic pattern)

- [ ] **Comparison Analysis Parallelization**
  - Stock data fetching already parallel (ThreadPoolExecutor)
  - But individual stock analyses are generated sequentially
  - Fix: Generate both analyses in parallel when neither is cached

### 9.3 Larger Efforts (1-2 Days Each)

- [ ] **CDN for Static Assets**
  - Cloudflare free tier in front of `permabullish.com`
  - Global edge caching, automatic compression, DDoS protection
  - Reduces latency for users outside the Render region

- [ ] **Background Report Generation**
  - Return "generating..." status immediately, poll for completion
  - Frees Gunicorn workers for other requests during AI generation
  - Better UX with progress indicator instead of blocking wait

- [ ] **Increase Gunicorn Workers**
  - Currently 2 workers — only 2 concurrent report generations before queueing
  - Increase to 4 workers (depends on Render plan memory)
  - Doubles concurrent request throughput

### 9.4 Future / Backlog

- [ ] **Redis Cache Layer** — Persistent cache across restarts, shared across instances
- [ ] **Pre-warm Popular Stocks** — Cache top 50 Nifty stocks on startup
- [ ] **Connection Pooling** — PgBouncer for PostgreSQL
- [ ] **Service Worker** — Offline support for viewed reports
- [ ] **Asset Optimization** — Minify CSS/JS, WebP images, critical CSS inlining

### Deliverables
- [ ] Chart endpoint cached (90% fewer Yahoo Finance calls)
- [ ] Database indexes on high-traffic queries
- [ ] API response compression enabled
- [ ] Provider fallback parallelized
- [ ] Optimized API response times

---

## Phase 10: WhatsApp Bot (Text)
**Status:** ✅ COMPLETE
**Completed:** March 26, 2026
**Priority:** High

### Objective
Build a fully automated WhatsApp bot for instant stock research — no app, no login, no friction. Primary distribution channel for Indian retail investors and sub-brokers.

### 10.1 Infrastructure ✅

- [x] Meta WhatsApp Cloud API (direct — no BSP, ₹0/month for user-initiated conversations)
- [x] Meta test number (`+1 555 139 4810`) used for development (5 recipient limit)
- [x] Production number migration pending (existing Permabullish WhatsApp Business App number)
- [x] FastAPI router `backend/whatsapp.py` mounted at `/whatsapp`
- [x] `GET /whatsapp/webhook` — Meta verification handshake
- [x] `POST /whatsapp/webhook` — HMAC-SHA256 signature validation
- [x] Environment variables: `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_WABA_ID`, `WHATSAPP_APP_SECRET`, `WHATSAPP_VERIFY_TOKEN`

### 10.2 Message Handling ✅

- [x] **Greeting detection** — "hi", "hello", "namaste" etc. → welcome message (English only)
- [x] **Stock search** — full name or ticker, reuses existing `search_stocks()`
- [x] **Disambiguation** — reply buttons (≤3 results) or interactive list (4–8 results)
- [x] **Session state** — `whatsapp_sessions` table, 5-min TTL
- [x] **Email linking** — auto-detected email text → links phone hash to user account
- [x] **Unhandled types** — voice/image/sticker → redirect to email, event flagged

### 10.3 Report Delivery ✅

- [x] **Report card image** — Pillow-generated PNG, live price via `yfinance fast_info`, 5-min cache
  - Endpoint: `GET /whatsapp/card/{ticker}.png?exchange=`
- [x] **Text report** — WhatsApp-formatted (bold `*`), thesis, metrics, recommendation, target price
  - Report link → `report.html?id=X` (content-gated for unauthenticated users)
- [x] **Action buttons** after every report: 📈 Price Chart | 📋 Results | 📰 Latest News
  - Chart: served from `GET /whatsapp/chart/{ticker}.png` (matplotlib, 6-month)
  - Results: last 4 quarters revenue + net income via `yfinance quarterly_income_stmt`
  - News: top 4 headlines via `yfinance.news`
  - All 3 **gated behind linked account**

### 10.4 Gating & Monthly Limits ✅

| Account State | Reports/Month | Action Buttons |
|---------------|---------------|----------------|
| Unlinked phone | 3 | Shown but gated |
| Linked Free | 5 | Fully unlocked |
| Linked Basic | 50 | Fully unlocked |
| Linked Pro | 100 | Fully unlocked |

- [x] `whatsapp_usage(phone_hash, month_year, report_count)` table tracks usage
- [x] Nudge messages at limit exhaustion + when blocked
- [x] Linking prompt sent once after first report

### 10.5 Account Mapping ✅

- [x] Phone numbers stored only as SHA-256 hashes (privacy)
- [x] Voluntary email-based linking (no OTP required — user replies with email)
- [x] `whatsapp_accounts(phone_hash, user_id, linked_at)` table
- [x] Linking unlocks higher limits + action buttons

### 10.6 Tracking & Analytics ✅

- [x] `whatsapp_events` table — all events logged with phone_hash, ticker, metadata, flagged flag
- [x] WhatsApp section added to daily/weekly cron email report (`scripts/send_user_report.py`)
  - Reports sent, new phones, active phones, accounts linked, blocked count, action taps, top stocks

### Deliverables
- ✅ WhatsApp bot live (test number)
- ✅ Stock reports via WhatsApp (card + text + action buttons)
- ✅ Monthly usage gating with upgrade nudges
- ✅ Phone ↔ account linking
- ✅ Full event tracking + daily/weekly metrics in email reports

### New Files
- `backend/whatsapp.py` — Full bot module (webhook, handlers, senders, image endpoints)

### Modified Files
- `backend/database.py` — 4 new tables + 8 new CRUD functions
- `backend/main.py` — Router registration
- `backend/config.py` — WhatsApp env vars
- `backend/requirements.txt` — matplotlib added
- `backend/scripts/send_user_report.py` — WhatsApp stats section
- `.env.example` — WhatsApp vars documented

### Pending
- [ ] Migrate production number (existing WhatsApp Business App) to Cloud API
- [ ] Add WhatsApp CTA to permabullish.com homepage and brokers landing page

---

## Phase 10.1: WhatsApp Voice Interface (Sarvam AI)
**Status:** 🔜 Planned (post-production-number migration)
**Priority:** Medium

### Objective
Extend the WhatsApp bot with voice input/output using Sarvam AI, enabling fully voice-driven stock research for users who prefer speaking over typing.

### Features Planned
- [ ] **Voice Out (TTS)** — Send audio summary as WhatsApp voice note (Sarvam Bulbul v2)
- [ ] **Voice In (STT)** — Accept voice notes as stock queries (Sarvam STT API)
- [ ] **Code-mixed queries** — "Reliance ka report bhejo" → RELIANCE, Hindi
- [ ] **Voice-to-voice** — Voice note in → audio report out, language matched automatically

### Cost Estimate
| Service | Pricing | Est. Monthly (1K uses) |
|---------|---------|------------------------|
| Sarvam TTS (Bulbul v2) | ₹15/10K chars | ~₹750 |
| Sarvam STT | ₹30/hr | ~₹150 |
| WhatsApp API | ₹0 (user-initiated) | ₹0 |

---

## Phase 10.5: Broker & Sub-Broker Outreach System
**Status:** 🔄 IN PROGRESS
**Priority:** High
**Target:** February-March 2026

### Objective
Build a data pipeline and outreach system to reach stock brokers, sub-brokers, and authorized persons (APs) across India via Telegram and WhatsApp — their preferred communication channels.

### 10.5.1 Data Collection ✅ COMPLETE

- [x] **SEBI Broker Scraper** (`scripts/scrape_sebi_brokers.py`)
  - Scrapes SEBI registered stock broker directory
  - 1,300+ unique brokers with emails, phones, addresses
  - Output: `sebi_brokers.csv`

- [x] **Multi-Broker Locator Scraper** (`scripts/scrape_broker_locators.py`)
  - Scrapes sub-broker/AP locator pages for Angel One, Motilal Oswal, Sharekhan, IIFL
  - Location-based search with phone numbers, addresses, landmarks
  - Reusable for any city: `--search "Mumbai, Maharashtra, India"`
  - Output: `brokers_{city}.csv`

- [x] **Bulk API Scrapers**
  - ICICI Direct APs: 1,312 records (`scripts/scrape_icicidirect_aps.py`)
  - 5Paisa APs: 94 records (`scripts/scrape_5paisa_ap.py`)
  - Kotak Securities: 1,000 branches/franchisees with emails (`scripts/scrape_kotak_branches.py`)
  - HDFC Securities: 161 branches with manager contacts (`scripts/scrape_hdfc_securities.py`)

- [x] **Top 10 cities nationwide scrape** ✅ COMPLETE
  - Angel One + Motilal Oswal + Sharekhan + IIFL across 10 cities
  - **2,133 unique sub-brokers/APs** with phone numbers, addresses, landmarks
  - Master CSV: `scripts/master_brokers.csv`
  - City breakdown:
    | City | Count |
    |------|-------|
    | Ahmedabad | 457 |
    | Mumbai | 305 |
    | Bengaluru | 261 |
    | Kolkata | 242 |
    | Pune | 209 |
    | Jaipur | 169 |
    | Hyderabad | 143 |
    | New Delhi | 140 |
    | Lucknow | 107 |
    | Chennai | 100 |
  - By broker: Motilal Oswal (1,116), Sharekhan (515), Angel One (426), IIFL (76)

### 10.5.2 Telegram Outreach ❌ NOT VIABLE

- [x] **Telegram Number Checker** (`scripts/check_telegram_numbers.py`) ✅ Built & Tested
  - Uses Telegram Client API (telethon) with `contacts.importContacts`
  - Batch processing with resume support, rate limiting, auto-cleanup
  - **Result: 1 out of 2,133 numbers on Telegram (0.05%)**
  - Broker locator numbers are office/auto-dialer numbers, not personal mobiles
  - **Conclusion: Telegram cold outreach is not viable for broker contacts**

### 10.5.3 In-Person Outreach (PRIMARY STRATEGY) 🔄 IN PROGRESS

**"Do things that don't scale"** — Physical visits to every sub-broker and AP, starting with Bengaluru.

- [x] **Bengaluru broker database** — 261 sub-brokers with full addresses, landmarks, phone numbers, hours
- [x] **Route-optimized visit list** — Brokers grouped by area/pincode for efficient daily routes
- [x] **Visit tracker spreadsheet** — Tracking: visited Y/N, interested Y/N, personal number, notes
- [x] **Printable leave-behind** — QR code to website + Telegram group, product summary

**Visit plan:**
- Target: 10-15 visits per day, 3-4 weeks to cover Bengaluru
- Approach: Walk in → demo product live on phone → show Hindi/Gujarati reports → collect personal number
- Goal: Get personal WhatsApp/phone number + sign them up on the spot
- After Bengaluru: Expand to other cities using same playbook

**Why this works:**
- Sub-brokers are local business owners — they respect in-person meetings
- Live demo is 100x more convincing than cold messages
- Personal numbers collected → WhatsApp/Telegram group invites actually work
- Trust-building that no digital outreach can match

### 10.5.4 WhatsApp Outreach (After In-Person)

- [ ] **WhatsApp Business API Setup**
  - Provider: Interakt, Wati, or AiSensy
  - Template message approval from Meta
  - Message: "Give your clients institutional-quality research in their language"

- [ ] **WhatsApp Broadcast System**
  - Import personal numbers collected from in-person visits
  - Send template messages (₹0.50-1/msg)
  - Track delivery, read receipts, responses

### 10.5.5 Email Outreach (Supplementary)

- [x] **Corporate email database** — 1,400+ emails (SEBI brokers, IIFL/HDFC managers)
- [x] **5 broker-focused email templates** (already built)
- [ ] Scale sending as domain warms up: 200 → 400 → 600/day

### Data Files
```
backend/scripts/
├── scrape_broker_locators.py          # Multi-broker locator scraper
├── scrape_sebi_brokers.py             # SEBI registered brokers
├── scrape_angelone_brokers.py         # Angel One specific (legacy)
├── scrape_icicidirect_aps.py          # ICICI Direct APs
├── scrape_5paisa_ap.py                # 5Paisa APs
├── scrape_kotak_branches.py           # Kotak branches/franchisees
├── scrape_hdfc_securities.py          # HDFC Securities branches
├── combine_broker_csvs.py             # Combine city CSVs → master list
├── check_telegram_numbers.py          # Telegram number checker (telethon)
├── master_brokers.csv                 # 2,133 unique brokers (all cities)
├── telegram_results.csv               # Telegram check results
├── brokers_bengaluru_karnataka_india.csv  # Per-city CSVs (10 cities)
├── brokers_mumbai_maharashtra_india.csv
├── brokers_ahmedabad_gujarat_india.csv
├── ... (8 more city CSVs)
├── sebi_brokers.csv
├── kotak_branches.csv
├── hdfc_securities_branches.csv
├── icicidirect_authorized_persons.csv
├── fivepaisa_authorized_persons.csv
└── angelone_brokers.csv
```

---

## Phase 11: Future Features (Post-Launch)
**Status:** Backlog
**Priority:** Low

### Potential Features

- [ ] **Chat with AI:** Follow-up questions about stocks
- [ ] **Price alerts:** Notify when stock hits target
- [ ] **Report alerts:** Notify when report is outdated
- [ ] **Portfolio tracking:** Track holdings and returns
- [x] **Comparison reports:** Compare two stocks side-by-side ✅ (Phase 7.6)
- [ ] **API access:** Programmatic access for Enterprise
- [ ] **Mobile app:** Native iOS/Android
- [x] **International stocks:** US market ✅ (Phase 8)
- [ ] **Performance optimization:** Caching, CDN, background jobs (Phase 9)
- [x] **WhatsApp bot + voice interface:** Sarvam AI integration ✅ (Phase 10)

---

## Timeline Summary

| Phase | Description | Status |
|-------|-------------|--------|
| 0 | Repository Cleanup | ✅ Complete |
| 1 | Core Product Enhancement | ✅ Complete |
| 2 | Subscription System | ✅ Complete |
| 3 | Payment Integration | ✅ Complete |
| 3.5 | Production Launch | ✅ Complete |
| 3.6 | Post-Launch Improvements | ✅ Complete |
| 4 | Data Enhancement | ✅ Complete |
| 5 | Pricing Analysis | ✅ Complete |
| 6 | ~~Landing Page~~ Mobile UX | Pending |
| 7 | Multi-Language | ✅ Complete |
| 7.5 | Security & Best Practices | 🔄 In Progress |
| 7.6 | Stock Comparison Tool | ✅ Complete |
| 7.8 | **Report Quality Enhancements** | 🔄 In Progress |
| 7.9 | Email/Password Authentication | ✅ Complete |
| 7.95 | **Shared Report Content Gate** | ✅ Complete |
| 8 | US Market Expansion | 📋 Planning |
| 9 | Performance Optimization | Backlog |
| 10 | WhatsApp Bot + Voice (Sarvam AI) | 📋 Planning |
| 11 | Future Features | Backlog |

---

## Admin & Operations Scripts

### User Management Scripts ✅

| Script | Purpose | Usage |
|--------|---------|-------|
| `scripts/export_users.py` | Export all users | `--google-only --emails-only` |
| `scripts/weekly_new_users.py` | New users report | `--days 7 --format csv` |

```bash
# Get all Google OAuth user emails
python scripts/export_users.py --google-only --emails-only

# Weekly new users report
python scripts/weekly_new_users.py --days 7

# Export as CSV
python scripts/weekly_new_users.py --format csv --output new_users.csv
```

### Email Scripts ✅

| Script | Purpose | Usage |
|--------|---------|-------|
| `scripts/send_reengagement_emails.py` | Re-engagement emails for inactive users + external contacts | `--dry-run --limit N` |
| `scripts/send_expiry_emails.py` | Expiry reminders for lapsed paid subscribers | `--dry-run --limit N` |
| `scripts/import_external_contacts.py` | Import CSV email lists for promotional campaigns | `<csv_path>` |
| `scripts/cleanup_bounced_emails.py` | Mark bounced/failed emails as inactive | `--dry-run --limit N` |
| `scripts/check_conversions.py` | Check external contacts who became users | - |

```bash
# Re-engagement emails (dry run)
python scripts/send_reengagement_emails.py --dry-run

# Expiry reminder emails (dry run)
python scripts/send_expiry_emails.py --dry-run

# Full run (all eligible users + external contacts)
python scripts/send_reengagement_emails.py
python scripts/send_expiry_emails.py

# Import external contacts from CSV
python scripts/import_external_contacts.py /path/to/emails.csv

# Cleanup bounced emails (dry run first)
python scripts/cleanup_bounced_emails.py --dry-run
python scripts/cleanup_bounced_emails.py

# Check conversion rate
python scripts/check_conversions.py
```

**Cron Setup (Render):**
```bash
# Run daily at 10 AM IST (4:30 AM UTC)
0 4 * * * cd /app/backend && python scripts/send_reengagement_emails.py
0 5 * * * cd /app/backend && python scripts/send_expiry_emails.py
```

### Data Sync Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `scripts/fundamentals_sync.py` | Sync stock fundamentals | `--symbol TCS` or full sync |

```bash
# Full sync (all 499 stocks)
python scripts/fundamentals_sync.py

# Single stock
python scripts/fundamentals_sync.py --symbol RELIANCE

# Test mode (no DB save)
python scripts/fundamentals_sync.py --test --symbol TCS
```

**MVP Status:** ✅ LIVE at permabullish.com

---

## Technical Architecture

### Production URLs
- **Frontend:** https://permabullish.com
- **API:** https://api.permabullish.com
- **Render Dashboard:** https://dashboard.render.com

### Key Files
- `backend/main.py` - FastAPI application
- `backend/report_generator.py` - AI report and comparison generation
- `backend/share_card.py` - Social sharing image generator (reports + comparisons)
- `backend/cashfree.py` - Payment integration
- `backend/email_service.py` - Email templates and sending (Resend)
- `backend/config.py` - Subscription tiers, email config, and settings
- `frontend/compare.html` - Stock comparison page
- `frontend/verify-email.html` - Email verification page
- `frontend/reset-password.html` - Password reset page
- `frontend/config.js` - Frontend configuration and payment form URLs
- `docs/ADMIN_GUIDE.md` - Enterprise user management guide

### Environment Variables (Production)
- `DATABASE_URL` - PostgreSQL connection string
- `ANTHROPIC_API_KEY` - Claude API key
- `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` - OAuth
- `CASHFREE_APP_ID` / `CASHFREE_SECRET_KEY` - Payments
- `CASHFREE_ENV=production` - Payment environment
- `RESEND_API_KEY` - Email service (Resend)
- `ENVIRONMENT=production` - App environment
- `FRONTEND_URL=https://permabullish.com`

---

## Notes

1. **Payment Forms vs Gateway:** Using Cashfree Payment Forms due to domain whitelisting requirements for Payment Gateway
2. **Recurring payments:** Not implemented - users pay upfront for subscription period
3. **Enterprise users:** Created manually via admin API endpoints
4. **Chat feature:** Subsumed by WhatsApp bot interface (Phase 10)

---

*This roadmap is subject to change based on user feedback and business priorities.*
