# Archive Plan - Permabullish Repository Cleanup

**Date:** January 30, 2025
**Purpose:** Document the cleanup process for pivoting permabullish-ai to focus solely on AI Stock Research

---

## Current Repository Structure

```
permabullish-ai/
├── .env.example
├── .git/
├── .gitignore
├── README.md
├── render.yaml
├── backend/           # KEEP - Stock research API
├── docs/              # KEEP - Documentation
├── frontend/          # KEEP - Stock research frontend
├── landing/           # REMOVE - Old multi-product landing page
├── mf-frontend/       # REMOVE - Mutual fund frontend
├── migrations/        # KEEP - Database migrations
├── pms-backend/       # REMOVE - PMS tracker backend
└── pms-frontend/      # REMOVE - PMS tracker frontend
```

---

## Items to Archive (Remove from Repo, Keep Locally)

### 1. MF Analytics Frontend
**Path:** `mf-frontend/`
**Reason:** Mutual fund features are out of scope for the pivot
**Archive to:** `F:\Dev\ClaudeProjects\_archive\permabullish-mf-frontend\`

### 2. PMS Tracker Backend
**Path:** `pms-backend/`
**Reason:** PMS tracking is out of scope for the pivot
**Archive to:** `F:\Dev\ClaudeProjects\_archive\permabullish-pms-backend\`

### 3. PMS Tracker Frontend
**Path:** `pms-frontend/`
**Reason:** PMS tracking is out of scope for the pivot
**Archive to:** `F:\Dev\ClaudeProjects\_archive\permabullish-pms-frontend\`

### 4. Old Landing Page
**Path:** `landing/`
**Reason:** Multi-product landing page no longer relevant
**Archive to:** `F:\Dev\ClaudeProjects\_archive\permabullish-landing-v1\`

---

## Items to Keep

### 1. Backend (`backend/`)
Stock research API - this is the core product

### 2. Frontend (`frontend/`)
Stock research web interface

### 3. Migrations (`migrations/`)
Database schema migrations

### 4. Documentation (`docs/`)
PRD, Roadmap, and other documentation

### 5. Configuration Files
- `.env.example`
- `.gitignore`
- `render.yaml` (will be updated)

---

## Archive Execution Steps

### Step 1: Create Archive Directory
```bash
mkdir -p "F:\Dev\ClaudeProjects\_archive"
```

### Step 2: Copy to Archive
```bash
# Copy MF frontend
cp -r permabullish-ai/mf-frontend "F:\Dev\ClaudeProjects\_archive\permabullish-mf-frontend"

# Copy PMS backend
cp -r permabullish-ai/pms-backend "F:\Dev\ClaudeProjects\_archive\permabullish-pms-backend"

# Copy PMS frontend
cp -r permabullish-ai/pms-frontend "F:\Dev\ClaudeProjects\_archive\permabullish-pms-frontend"

# Copy old landing page
cp -r permabullish-ai/landing "F:\Dev\ClaudeProjects\_archive\permabullish-landing-v1"
```

### Step 3: Remove from Repository
```bash
cd permabullish-ai

# Remove directories
rm -rf mf-frontend
rm -rf pms-backend
rm -rf pms-frontend
rm -rf landing
```

### Step 4: Update render.yaml
Remove service definitions for:
- `permabullish-mf` (MF static site)
- `permabullish-pms-api` (PMS API)
- `permabullish-pms` (PMS static site)

Keep only:
- `permabullish-api` (Stock research API)
- `permabullish-web` (Stock research frontend)
- `permabullish-db` (PostgreSQL database)

### Step 5: Update README.md
Replace with new product description focused on AI Stock Researcher

### Step 6: Commit Changes
```bash
git add -A
git commit -m "Pivot to AI Stock Researcher - archive MF and PMS components

- Remove mf-frontend (Mutual Fund analytics)
- Remove pms-backend (PMS tracker API)
- Remove pms-frontend (PMS tracker UI)
- Remove old landing page
- Update render.yaml for single-product deployment
- Update documentation

Archived code available locally at:
F:\Dev\ClaudeProjects\_archive\"
```

---

## render.yaml Update

### Before (Multi-Product)
```yaml
services:
  # Stock Research API
  - type: web
    name: permabullish-api
    ...

  # MF Frontend (REMOVE)
  - type: web
    name: permabullish-mf
    ...

  # PMS API (REMOVE)
  - type: web
    name: permabullish-pms-api
    ...

  # PMS Frontend (REMOVE)
  - type: web
    name: permabullish-pms
    ...
```

### After (Single Product)
```yaml
services:
  # Stock Research API
  - type: web
    name: permabullish-api
    runtime: python
    buildCommand: pip install -r backend/requirements.txt
    startCommand: cd backend && gunicorn main:app
    envVars:
      - key: ANTHROPIC_API_KEY
        sync: false
      - key: GOOGLE_CLIENT_ID
        sync: false
      - key: GOOGLE_CLIENT_SECRET
        sync: false
      - key: DATABASE_URL
        fromDatabase:
          name: permabullish-db
          property: connectionString

  # Stock Research Frontend
  - type: web
    name: permabullish-web
    runtime: static
    buildCommand: echo "Static site"
    staticPublishPath: frontend
    routes:
      - type: rewrite
        source: /*
        destination: /index.html

databases:
  - name: permabullish-db
    plan: starter
```

---

## Post-Archive Verification

After completing the archive:

1. [ ] Verify local archive exists and is complete
2. [ ] Verify repository only contains stock research code
3. [ ] Run backend locally to ensure no broken imports
4. [ ] Deploy to Render staging to verify
5. [ ] Test all stock research functionality

---

## Rollback Plan

If needed, restore from local archive:

```bash
# Restore any component
cp -r "F:\Dev\ClaudeProjects\_archive\permabullish-mf-frontend" permabullish-ai/mf-frontend
```

Or restore from git history:
```bash
git checkout HEAD~1 -- mf-frontend/
```

---

## Notes

- The standalone `PMSTracker` and `MFAnalytics` projects in `F:\Dev\ClaudeProjects\` are separate and unaffected
- The `equity-research-generator` project remains as the development environment until Phase 3
- Archive is for reference only - do not plan to restore these components

---

*Archive plan prepared for Phase 0 of the Permabullish pivot.*
