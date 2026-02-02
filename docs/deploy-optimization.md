# Deploy Optimization Strategies

A comprehensive guide to making Render deploys faster and more performant.

## Current State

- **Build command**: `pip install -r requirements.txt` (no caching)
- **Services rebuilt on push to main**: 6 (1 API + 5 cron jobs)
- **Heavy dependencies**: psycopg2-binary, Pillow, yfinance, pandas, cryptography

---

## Build Speed Optimizations

### 1. Dependency Caching

**Pip cache directory** - Use Render's persistent cache:
```yaml
buildCommand: |
  pip install --upgrade pip
  pip install --cache-dir /opt/render/.cache/pip -r requirements.txt
```

**Requirements hash** - Only reinstall if requirements.txt changes (Dockerfile approach):
```dockerfile
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
```

**Pre-built wheels** - Avoid compiling from source:
```bash
pip install --only-binary :all: -r requirements.txt
```

### 2. Smaller Dependency Footprint

**Separate requirements files:**
```
requirements-api.txt      # Full stack for API
requirements-cron.txt     # Minimal: psycopg2, resend, pytz
requirements-common.txt   # Shared deps
```

Example `requirements-cron.txt`:
```
psycopg2-binary>=2.9.9
resend>=0.7.0
pytz>=2024.1
```

**Audit unused deps** - Check what's actually imported:
```bash
pip install pipreqs
pipreqs backend/ --print
```

### 3. Docker-based Deploys

**Multi-stage Dockerfile:**
```dockerfile
# Build stage
FROM python:3.11-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user -r requirements.txt

# Runtime stage
FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .
ENV PATH=/root/.local/bin:$PATH
CMD ["gunicorn", "main:app", ...]
```

**Pre-built base image:**
```dockerfile
# Push to Docker Hub once
FROM python:3.11-slim
RUN pip install fastapi uvicorn anthropic yfinance pillow psycopg2-binary ...
# Then use as base for deploys
```

### 4. Reduce Rebuild Triggers

**Path filters in render.yaml** (if supported) or use separate branches:
- Only rebuild API when `backend/**` changes
- Only rebuild frontend when `frontend/**` changes
- Cron jobs rarely need rebuilds

**Ignore patterns** - Don't rebuild on:
- README.md changes
- docs/ changes
- .gitignore changes

---

## Runtime Performance

### 5. Faster Startup

**Lazy imports** - Don't import heavy modules at top level:
```python
# Instead of: import yfinance as yf
def fetch_stock_data():
    import yfinance as yf  # Import when needed
    ...
```

**Gunicorn preload** - Load app once, fork workers:
```yaml
startCommand: gunicorn main:app --preload --workers 2 ...
```

**Connection pooling** - Already using psycopg2, ensure pool is configured.

### 6. Static Assets

**CDN options** (free tier available):
- Cloudflare Pages
- Vercel
- Netlify

Benefits:
- Global edge caching
- Instant deploys (just static files)
- Free SSL, custom domains

**Asset hashing** for long cache TTLs:
```yaml
headers:
  - path: /assets/*
    name: Cache-Control
    value: public, max-age=31536000, immutable
```

---

## Architecture Changes

### 7. Monorepo Split

**Option A: Separate repos**
- `permabullish-api` - Backend only
- `permabullish-web` - Frontend only
- Independent deploy cycles

**Option B: Separate branches**
```
main          # Development
deploy/api    # Cherry-pick API changes
deploy/web    # Cherry-pick frontend changes
deploy/cron   # Rarely updated
```

### 8. Serverless for Cron Jobs

**Options:**
- Render Background Workers (current)
- AWS Lambda + EventBridge
- Cloudflare Workers + Cron Triggers
- GitHub Actions scheduled workflows (free)

**GitHub Actions example:**
```yaml
name: Daily Report
on:
  schedule:
    - cron: '0 9 * * *'
jobs:
  report:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install psycopg2-binary resend
      - run: python scripts/send_user_report.py daily
        env:
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
```

### 9. Preview Environments

**PR previews** - Test changes before merging
**Feature flags** - Deploy to production, enable gradually
**Skip staging** - If confident in tests

---

## Quick Wins Matrix

| Strategy | Effort | Impact | Notes |
|----------|--------|--------|-------|
| Pip caching | Low | Medium | Single line change |
| Separate cron requirements | Low | Medium | Create new file, update render.yaml |
| Move frontend to Vercel | Medium | High | Free, instant deploys, global CDN |
| Path filters / branches | Low | High | Prevent unnecessary rebuilds |
| Gunicorn --preload | Low | Low | Faster worker startup |
| Dockerfile | Medium | High | Best caching, but more complexity |
| Serverless cron (GitHub Actions) | Medium | Medium | Free, no cold builds |
| Pre-built Docker base image | High | High | Ultimate solution for speed |

---

## Implementation Priority

### Phase 1: Quick wins (do now)
1. Add pip caching to buildCommand
2. Add `--preload` to gunicorn

### Phase 2: Medium effort (next sprint)
3. Create separate `requirements-cron.txt`
4. Move frontend to Vercel/Cloudflare Pages
5. Set up path-based deploy triggers

### Phase 3: Major refactor (future)
6. Dockerize the API
7. Move cron jobs to GitHub Actions
8. Pre-built base image on Docker Hub

---

## Monitoring Deploy Times

Track these metrics:
- Build time (pip install duration)
- Deploy time (total from push to live)
- Cold start time (first request after deploy)

Render dashboard shows build logs with timestamps.
