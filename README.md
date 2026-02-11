# Permabullish - AI Stock Researcher

AI-powered equity research reports for Indian stocks. Get institutional-quality stock analysis instantly.

## Features

- **AI-Powered Reports**: Claude AI generates professional research reports with investment recommendations
- **Indian Stock Coverage**: NSE/BSE stocks with real-time pricing
- **Report Caching**: Shared reports across users for efficiency
- **Subscription Tiers**: Guest (1 report), Free (5 reports), Basic (50/mo), Pro (100/mo)
- **Google Sign-In**: Simple authentication with Google OAuth
- **Watchlist**: Track stocks and generate reports on demand
- **Multi-Language**: English, Hindi, Gujarati & Kannada

## Tech Stack

- **Backend**: FastAPI (Python)
- **Database**: PostgreSQL (production) / SQLite (development)
- **Frontend**: Static HTML/JS with Tailwind CSS
- **AI**: Claude API (Anthropic)
- **Auth**: Google OAuth + JWT
- **Payments**: Cashfree
- **Hosting**: Render

## Getting Started

### Prerequisites

- Python 3.11+
- Anthropic API key
- Google OAuth credentials

### Local Development

1. **Clone and set up**
   ```bash
   git clone https://github.com/yourusername/permabullish-ai.git
   cd permabullish-ai/backend
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure environment**
   ```bash
   cp ../.env.example .env
   # Edit .env with your API keys
   ```

3. **Run the server**
   ```bash
   python main.py
   ```

4. **Access the app**
   - API: http://localhost:8000
   - Docs: http://localhost:8000/docs
   - Frontend: http://localhost:8000/static/index.html

## Project Structure

```
permabullish-ai/
├── backend/
│   ├── main.py              # FastAPI application
│   ├── auth.py              # Google OAuth + JWT
│   ├── database.py          # PostgreSQL/SQLite
│   ├── report_generator.py  # Claude AI integration
│   └── requirements.txt
├── frontend/
│   ├── index.html           # Login page
│   ├── dashboard.html       # User dashboard
│   ├── generate.html        # Report generation
│   └── report.html          # Report viewer
├── docs/
│   ├── PRD.md               # Product requirements
│   ├── ROADMAP.md           # Development roadmap
│   └── ARCHIVE_PLAN.md      # Migration notes
├── migrations/
│   └── *.sql                # Database migrations
├── render.yaml              # Render deployment config
└── README.md
```

## Subscription Tiers

| Tier | Reports | Price |
|------|---------|-------|
| Guest | 1 (lifetime) | Free |
| Free | 5 (lifetime) | Free |
| Basic | 50/month | ₹999/mo or ₹7,499/yr |
| Pro | 100/month | ₹1,499/mo or ₹9,999/yr |
| Enterprise | Unlimited | Contact: mail@mayaskara.com |

## Documentation

- [Product Requirements (PRD)](docs/PRD.md)
- [Development Roadmap](docs/ROADMAP.md)

## License

MIT License
