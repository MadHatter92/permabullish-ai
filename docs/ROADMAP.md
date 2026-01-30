# Permabullish - Product Roadmap
## AI Stock Researcher

**Version:** 2.1
**Last Updated:** January 30, 2026

---

## Overview

This roadmap outlines the development phases for Permabullish AI Stock Researcher. We're building on the existing `equity-research-generator` codebase and will eventually consolidate everything into the `permabullish-ai` repository.

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
**Status:** Pending
**Priority:** High
**Dependencies:** Phase 1

### Objective
Implement tiered subscription system with usage limits.

### 2.1 Subscription Tiers

- [ ] Define tier limits in config:
  ```python
  TIERS = {
      'free': {'reports': 3, 'is_lifetime': True},
      'basic': {'reports': 10, 'is_lifetime': False},
      'pro': {'reports': 50, 'is_lifetime': False},
      'enterprise': {'reports': float('inf'), 'is_lifetime': False}
  }
  ```
- [ ] Create `subscriptions` table
- [ ] Implement subscription status checking
- [ ] Add subscription expiry handling

### 2.2 Usage Tracking

- [ ] Enhance `usage` table for monthly tracking
- [ ] Reset usage on 1st of each month (paid tiers)
- [ ] Implement quota enforcement on report generation
- [ ] Create usage display component
- [ ] Add "X reports remaining" indicator

### 2.3 Pricing Page

- [ ] Design pricing page with tier comparison
- [ ] Show: Free (3 reports), Basic (10/mo), Pro (50/mo), Enterprise (contact us)
- [ ] Add payment period options: 1 month, 6 months, 12 months
- [ ] Display "Contact us" for Enterprise tier
- [ ] Placeholder for actual prices (TBD after Phase 5 analysis)

### 2.4 Upgrade Flow

- [ ] Create upgrade prompts when quota exhausted
- [ ] Build subscription selection UI
- [ ] Implement subscription API endpoints
- [ ] Add subscription status to user profile

### Deliverables
- Working tier system with limits
- Usage tracking and display
- Pricing page (prices TBD)
- Upgrade flow UI

---

## Phase 3: Payment Integration
**Status:** Pending
**Priority:** High
**Dependencies:** Phase 2

### Objective
Integrate Cashfree payment gateway for subscription payments.

### 3.1 Cashfree Setup

- [ ] Create Cashfree merchant account
- [ ] Obtain API credentials (Key, Secret)
- [ ] Configure webhook endpoints
- [ ] Set up test/sandbox environment

### 3.2 Payment Flow

- [ ] Implement checkout initiation endpoint
- [ ] Create payment page/redirect
- [ ] Handle Cashfree webhooks:
  - Payment success
  - Payment failure
  - Payment pending
- [ ] Update subscription on successful payment

### 3.3 Payment UI

- [ ] Build checkout page with plan summary
- [ ] Show payment options (1/6/12 months)
- [ ] Display total amount and any discounts
- [ ] Add payment success/failure pages
- [ ] Email confirmation (optional)

### 3.4 Subscription Management

- [ ] Create "My Subscription" page
- [ ] Show current plan, expiry date, usage
- [ ] Add renewal prompts before expiry
- [ ] Handle subscription expiry gracefully

### Deliverables
- Working Cashfree integration
- Complete payment flow
- Subscription management UI
- Webhook handling

---

## Phase 4: Data Enhancement
**Status:** Pending
**Priority:** Medium
**Dependencies:** Phase 1

### Objective
Improve stock data quality with Screener.in integration.

### 4.1 Screener.in Scraper

- [ ] Build Screener.in scraper using Puppeteer/Playwright
- [ ] Extract key data:
  - Financials (quarterly, annual)
  - Ratios (PE, PB, ROE, etc.)
  - Shareholding patterns
  - Peer comparison
- [ ] Store in `screener_data` table
- [ ] Handle rate limiting and authentication

### 4.2 Monthly Scrape Job

- [ ] Create scraper script for batch processing
- [ ] Set up monthly cron job (1st of month)
- [ ] Cover major indices: Nifty 500, BSE 500
- [ ] Add incremental update capability
- [ ] Log scraping status and errors

### 4.3 Data Integration

- [ ] Modify report generator to use Screener data
- [ ] Fall back to Yahoo Finance if Screener data missing
- [ ] Enhance AI prompt with richer data
- [ ] Improve report quality with detailed financials

### Deliverables
- Working Screener.in scraper
- Monthly automated scraping
- Enhanced reports with better data

---

## Phase 5: Pricing Analysis
**Status:** Pending
**Priority:** Medium
**Dependencies:** Phase 2, Phase 3

### Objective
Determine optimal pricing based on token consumption and costs.

### 5.1 Token Usage Analysis

- [ ] Log token usage per report generation
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
- [ ] Define pricing for each tier
- [ ] Set discount levels for 6/12 month subscriptions
- [ ] Update pricing page with actual prices
- [ ] A/B test pricing if possible

### 5.4 Implementation

- [ ] Update Cashfree checkout with final prices
- [ ] Configure subscription amounts
- [ ] Add promotional/launch pricing if desired

### Deliverables
- Token usage analytics
- Cost model spreadsheet
- Final pricing decision
- Updated payment integration

---

## Phase 6: Landing Page & Marketing
**Status:** Pending
**Priority:** Medium
**Dependencies:** Phase 2

### Objective
Create compelling landing page for conversions.

### 6.1 Landing Page Design

- [ ] Hero section with value proposition
- [ ] Feature highlights:
  - AI-powered analysis
  - Instant reports
  - Professional quality
- [ ] Sample report preview
- [ ] Pricing section
- [ ] Testimonials/social proof (when available)
- [ ] FAQ section
- [ ] Footer with links

### 6.2 Landing Page Development

- [ ] Build with React + Tailwind (or static HTML)
- [ ] Implement responsive design
- [ ] Add animations and interactions
- [ ] Optimize for performance
- [ ] SEO optimization

### 6.3 Conversion Optimization

- [ ] Add Google sign-in CTA prominently
- [ ] Show "3 free reports" incentive
- [ ] Create urgency/scarcity elements
- [ ] A/B test different headlines

### Deliverables
- Production-ready landing page
- Mobile-optimized design
- SEO-friendly implementation

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

## Migration Plan

### From equity-research-generator to permabullish-ai

1. **Phase 0:** Clean permabullish-ai repo, remove MF/PMS code
2. **Phase 1-3:** Develop in equity-research-generator
3. **After Phase 3:** Merge code into permabullish-ai
4. **Update render.yaml:** Point to new repo structure
5. **Deprecate:** Archive equity-research-generator

### Git Strategy

```
equity-research-generator (development)
         |
         | (merge after Phase 3)
         v
permabullish-ai (production)
```

---

## Timeline Summary

| Phase | Description | Duration | Status |
|-------|-------------|----------|--------|
| 0 | Repository Cleanup | 1 day | ✅ Complete |
| 1 | Core Product Enhancement | 1 day | ✅ Complete |
| 2 | Subscription System | 1 week | Pending |
| 3 | Payment Integration | 1 week | Pending |
| 4 | Data Enhancement | 1-2 weeks | Pending |
| 5 | Pricing Analysis | 3-5 days | Pending |
| 6 | Landing Page | 1 week | Pending |
| 7 | Multi-Language | 1 week | Future |
| 8 | Future Features | Ongoing | Backlog |

**Completed:** Phases 0-1 (January 30, 2026)
**Remaining to MVP (Phases 2-6):** 4-6 weeks

---

## Dependencies & Blockers

| Dependency | Blocks | Status |
|------------|--------|--------|
| Cashfree API credentials | Phase 3 | Waiting for user |
| Screener.in access | Phase 4 | To be set up |
| Final pricing decision | Phase 5 | After analysis |
| Logo/branding assets | Phase 6 | Existing available |

---

## Notes

1. **Development happens in equity-research-generator** until Phase 3 is complete
2. **Pricing is TBD** - placeholder prices until Phase 5 analysis
3. **Recurring payments** - Not in initial scope, users charged upfront
4. **Chat feature** - Explicitly deferred to post-launch

---

*This roadmap is subject to change based on user feedback and business priorities.*
