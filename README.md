# Permabullish

AI-powered investment research platform for Indian markets.

## Features

### Phase 1 (Current)
- **Stock Research Generator**: AI-powered equity research reports for Indian stocks
  - Company analysis with Claude AI
  - Bull/bear case analysis
  - Valuation metrics
  - Risk assessment

### Phase 2 (Planned)
- **PMS Tracker**: Portfolio Management Services performance tracking

### Phase 3 (Planned)
- **MF Analytics**: Mutual fund analysis and comparison tools

### Phase 4 (Planned)
- **Subscription/Paywall**: Stripe integration for premium features

## Architecture

```
permabullish.com (Static Site)
         |
         v
api.permabullish.com (FastAPI)
    +-- /api/research/*  -> Stock Research (Phase 1)
    +-- /api/pms/*       -> PMS Tracker (Phase 2)
    +-- /api/mf/*        -> MF Analytics (Phase 3)
         |
         v
PostgreSQL Database (Render)
```

## Tech Stack

- **Backend**: FastAPI (Python)
- **Frontend**: Static HTML/JS with Tailwind CSS
- **Database**: PostgreSQL (production) / SQLite (development)
- **AI**: Claude API (Anthropic)
- **Hosting**: Render
- **Auth**: Google OAuth + JWT

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js (optional, for frontend development)
- Anthropic API key

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/permabullish-ai.git
   cd permabullish-ai
   ```

2. **Set up Python environment**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   cp ../.env.example .env
   # Edit .env with your values (at minimum, set ANTHROPIC_API_KEY)
   ```

4. **Run the development server**
   ```bash
   python main.py
   # Or with uvicorn:
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

5. **Access the application**
   - API: http://localhost:8000
   - API Docs: http://localhost:8000/docs
   - Frontend: http://localhost:8000/static/index.html

### Running with PostgreSQL locally

1. Install PostgreSQL
2. Create a database:
   ```sql
   CREATE DATABASE permabullish_dev;
   ```
3. Set DATABASE_URL in .env:
   ```
   DATABASE_URL=postgresql://user:password@localhost:5432/permabullish_dev
   ```
4. Run migrations:
   ```bash
   psql -d permabullish_dev -f ../migrations/001_initial_schema.sql
   ```

## Deployment

### Render Deployment

1. **Fork/push to GitHub**

2. **Create Render Blueprint**
   - Go to Render Dashboard
   - New > Blueprint
   - Connect your repository
   - Render will read `render.yaml` and create all services

3. **Set environment variables**
   In Render Dashboard, set these for each API service:
   - `ANTHROPIC_API_KEY`
   - `GOOGLE_CLIENT_ID`
   - `GOOGLE_CLIENT_SECRET`

4. **Update OAuth redirect URIs**
   In Google Cloud Console, add:
   - Production: `https://permabullish-api.onrender.com/api/auth/google/callback`
   - Staging: `https://permabullish-api-staging.onrender.com/api/auth/google/callback`

### Deployment Workflow

```
[Local Development]
      |
      v (push to staging branch)
[Staging Environment] <- Test here
      |
      v (merge to main)
[Production Environment]
```

## Project Structure

```
permabullish-ai/
+-- backend/
|   +-- main.py              # FastAPI application
|   +-- auth.py              # Authentication + subscription
|   +-- database.py          # PostgreSQL/SQLite abstraction
|   +-- config.py            # Environment configuration
|   +-- report_generator.py  # Claude AI integration
|   +-- yahoo_finance.py     # Stock data fetching
|   +-- requirements.txt     # Python dependencies
|
+-- frontend/
|   +-- index.html           # Login page
|   +-- dashboard.html       # User dashboard
|   +-- generate.html        # Report generation
|   +-- report.html          # Report viewer
|   +-- config.js            # Environment detection
|
+-- migrations/
|   +-- 001_initial_schema.sql  # PostgreSQL schema
|
+-- render.yaml              # Render deployment config
+-- .env.example             # Environment template
+-- README.md                # This file
```

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login with email/password
- `GET /api/auth/me` - Get current user info
- `GET /api/auth/google/login` - Initiate Google OAuth
- `GET /api/auth/google/callback` - Google OAuth callback

### Stock Research
- `GET /api/stocks/search?q=` - Search Indian stocks
- `GET /api/stocks/{symbol}` - Get stock preview
- `POST /api/reports/generate` - Generate AI research report
- `GET /api/reports` - List user's reports
- `GET /api/reports/{id}` - Get report details
- `GET /api/reports/{id}/html` - Get report HTML
- `DELETE /api/reports/{id}` - Delete report

### Usage
- `GET /api/usage` - Get user's usage stats
- `GET /api/usage/anonymous` - Get anonymous usage stats

### Health
- `GET /api/health` - Service health check

## Subscription Tiers

| Tier | Reports/Month | Stock Research | MF Analytics | PMS Tracker |
|------|---------------|----------------|--------------|-------------|
| Free | 20 | Yes | No | No |
| Pro | 100 | Yes | Yes | Yes |
| Enterprise | 1000 | Yes | Yes | Yes + API |

## Cost Estimate

| Service | Monthly Cost |
|---------|-------------|
| Production API (Render Starter) | $7 |
| Production DB (Render Starter) | $7 |
| Staging (Free tier) | $0 |
| Static Sites | $0 |
| Claude API (usage-based) | ~$10-50 |
| **Total** | **~$25-65** |

## Contributing

1. Create a feature branch from `staging`
2. Make your changes
3. Test locally
4. Push to `staging` branch
5. Test on staging environment
6. Create PR to merge to `main`

## License

MIT License - See LICENSE file for details.
