# Permabullish - Product Roadmap
## AI Stock Researcher

**Version:** 3.0
**Last Updated:** January 31, 2026

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
- [x] Show: Free (3 reports), Basic (10/mo), Pro (50/mo), Enterprise (contact us)
- [x] Add payment period options: 1 month, 6 months, 12 months
- [x] Display savings percentages for longer periods
- [x] "Contact us" for Enterprise tier

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
- [x] Created 6 payment forms for all plan/period combinations:
  - Basic: Monthly, 6-Months, Yearly
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
- [x] **Re-engagement Email System**
  - 5 rotating templates + weekly digest template
  - Days 1-14: Daily emails (if inactive 7+ days)
  - Days 15-180: Weekly emails (if inactive 7+ days)
  - Cron script: `scripts/send_reengagement_emails.py`
  - IST timezone support
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

### Deliverables
- ✅ Complete email automation system
- ✅ Fiscally-grounded AI reports
- ✅ Improved stock search
- ✅ Legal compliance (disclaimers)
- ✅ Bug fixes for regeneration and sharing

### Environment Variables (New)
- `RESEND_API_KEY` - Email service API key

### Pending (Email System)
- [ ] DNS verification for permabullish.com (SPF, DKIM, DMARC)
- [ ] Set up cron job for re-engagement emails on Render

---

## Phase 4: Data Enhancement
**Status:** 🔄 IN PROGRESS
**Priority:** High
**Dependencies:** Phase 1

### Objective
Improve stock data quality and coverage.

### 4.1 Stock Coverage Expansion ✅

- [x] Create Nifty 500 stock list (`data/nifty500_stocks.json` - 499 stocks)
- [x] Expand Tickertape slug mappings (291 stocks, 58% coverage)
- [x] Update stock search to use full Nifty 500 list
- [x] Add newer listings (Swiggy, Nykaa, etc.)

### 4.2 Fundamentals Data Scraper ✅

- [x] Build fundamentals fetcher (`scripts/fundamentals_sync.py`)
- [x] Extract key data: P/E, ROE, ROCE, quarterly results, shareholding
- [x] Create `stock_fundamentals` table schema
- [x] Handle rate limiting (0.5s delay between requests)
- [x] Support single-stock and batch sync modes

### 4.3 Initial Data Sync 🔄

- [x] Database operations module (`fundamentals_db.py`)
- [ ] Run initial sync for all 499 stocks (IN PROGRESS)
- [ ] Verify data quality

### 4.4 Monthly Refresh Job

- [ ] Set up Render cron job (1st of month)
- [ ] Or use GitHub Actions as free alternative
- [ ] Add on-demand refresh for stale data (>45 days)

### 4.5 Report Generator Integration

- [ ] Modify report generator to use cached fundamentals
- [ ] Fall back to Yahoo Finance for missing data
- [ ] Enhance AI prompt with richer fundamentals

### Deliverables
- ✅ 499 Nifty 500 stocks searchable
- ✅ Fundamentals sync infrastructure
- 🔄 Initial data population
- Pending: Monthly cron job
- Pending: Report generator integration

---

## Phase 5: Pricing Analysis
**Status:** Partially Complete
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

- [ ] Research competitor pricing
- [ ] Validate current pricing (Basic ₹199/mo, Pro ₹499/mo)
- [ ] Analyze discount levels for 6/12 month subscriptions
- [ ] Adjust pricing if needed based on analysis

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
**Status:** Future
**Priority:** Low
**Dependencies:** Phase 1-6 complete

### Objective
Add Hindi and Gujarati language support for reports.

### 7.1 Language Selection

- [ ] Add language dropdown to report generation
- [ ] Options: English, Hindi, Gujarati
- [ ] Store user language preference
- [ ] Remember last selected language

### 7.2 Report Translation

- [ ] Modify AI prompt to generate reports in selected language
- [ ] Test quality of Hindi/Gujarati outputs
- [ ] Consider post-processing translation if needed
- [ ] Handle mixed language (company names in English)

### 7.3 UI Localization

- [ ] Translate UI strings (optional)
- [ ] Right-to-left support (not needed for Hindi/Gujarati)
- [ ] Language-specific formatting

### Deliverables
- Language selection UI
- Reports in Hindi and Gujarati
- Quality assurance for translations

---

## Phase 8: Future Features (Post-Launch)
**Status:** Backlog
**Priority:** Low

### Potential Features

- [ ] **Chat with AI:** Follow-up questions about stocks
- [ ] **Price alerts:** Notify when stock hits target
- [ ] **Report alerts:** Notify when report is outdated
- [ ] **Portfolio tracking:** Track holdings and returns
- [ ] **Comparison reports:** Compare multiple stocks
- [ ] **API access:** Programmatic access for Enterprise
- [ ] **Mobile app:** Native iOS/Android
- [ ] **International stocks:** US, UK markets

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
| 4 | Data Enhancement | 🔄 In Progress |
| 5 | Pricing Analysis | Partial |
| 6 | ~~Landing Page~~ Mobile UX | Pending |
| 7 | Multi-Language | Future |
| 8 | Future Features | Backlog |

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
| `scripts/send_reengagement_emails.py` | Send re-engagement emails | `--dry-run --limit N` |

```bash
# Dry run (see what would be sent)
python scripts/send_reengagement_emails.py --dry-run

# Send to first 10 eligible users
python scripts/send_reengagement_emails.py --limit 10

# Full run (all eligible users)
python scripts/send_reengagement_emails.py
```

**Cron Setup (Render):**
```bash
# Run daily at 10 AM IST (4:30 AM UTC)
0 4 * * * cd /app/backend && python scripts/send_reengagement_emails.py
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
- `backend/share_card.py` - Social sharing image generator
- `backend/cashfree.py` - Payment integration
- `backend/email_service.py` - Email templates and sending (Resend)
- `backend/config.py` - Subscription tiers, email config, and settings
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
4. **Chat feature:** Explicitly deferred to post-launch (Phase 8)

---

*This roadmap is subject to change based on user feedback and business priorities.*
