"""
Configuration module for Permabullish API.
Supports multiple environments: development, staging, production.
"""

import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Environment
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
IS_PRODUCTION = ENVIRONMENT == "production"
IS_STAGING = ENVIRONMENT == "staging"

# Database
# PostgreSQL URL for Render (automatically set by Render)
# For local dev, leave empty to use SQLite
DATABASE_URL = os.getenv("DATABASE_URL", "")

# JWT Settings
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production-abc123xyz")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

# Claude API
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Usage Limits
MONTHLY_REPORT_LIMIT = int(os.getenv("MONTHLY_REPORT_LIMIT", "20"))
ANONYMOUS_REPORT_LIMIT = int(os.getenv("ANONYMOUS_REPORT_LIMIT", "3"))

# Google OAuth Settings
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")

# Dynamic redirect URI based on environment
if IS_PRODUCTION:
    GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "https://api.permabullish.com/api/auth/google/callback")
    FRONTEND_URL = os.getenv("FRONTEND_URL", "https://permabullish.com")
elif IS_STAGING:
    GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "https://permabullish-api-staging.onrender.com/api/auth/google/callback")
    FRONTEND_URL = os.getenv("FRONTEND_URL", "https://permabullish-web-staging.onrender.com")
else:
    GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/auth/google/callback")
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:8000/static")

# Yahoo Finance - Indian stock suffixes
NSE_SUFFIX = ".NS"
BSE_SUFFIX = ".BO"

# Alpha Vantage API (backup stock data provider)
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY", "")

# CORS Origins - Always include production URLs to handle env var misconfiguration
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8000",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8000",
    # Always include Render URLs regardless of environment
    "https://permabullish.com",
    "https://www.permabullish.com",
    "https://api.permabullish.com",
    "https://permabullish-web.onrender.com",
    "https://permabullish-api.onrender.com",
]

if IS_STAGING:
    CORS_ORIGINS.extend([
        "https://permabullish-web-staging.onrender.com",
        "https://permabullish-api-staging.onrender.com",
    ])

# Add FRONTEND_URL to allowed origins if it's not already there
if FRONTEND_URL and FRONTEND_URL not in CORS_ORIGINS:
    CORS_ORIGINS.append(FRONTEND_URL)

# Cashfree Configuration (for payments)
CASHFREE_APP_ID = os.getenv("CASHFREE_APP_ID", "")
CASHFREE_SECRET_KEY = os.getenv("CASHFREE_SECRET_KEY", "")
CASHFREE_ENV = os.getenv("CASHFREE_ENV", "sandbox")  # sandbox or production

# Report freshness threshold (days)
REPORT_FRESHNESS_DAYS = 15

# Subscription Tiers
SUBSCRIPTION_TIERS = {
    "free": {
        "reports_limit": 3,
        "is_lifetime": True,  # Free tier is lifetime limit, not monthly
        "features": {
            "stock_research": True,
            "watchlist": True,
        }
    },
    "basic": {
        "reports_limit": 10,
        "is_lifetime": False,  # Monthly limit
        "features": {
            "stock_research": True,
            "watchlist": True,
        }
    },
    "pro": {
        "reports_limit": 50,
        "is_lifetime": False,
        "features": {
            "stock_research": True,
            "watchlist": True,
        }
    },
    "enterprise": {
        "reports_limit": 10000,  # Effectively unlimited
        "is_lifetime": False,
        "features": {
            "stock_research": True,
            "watchlist": True,
            "api_access": True,
        }
    }
}

print(f"Permabullish API Configuration:")
print(f"  Environment: {ENVIRONMENT}")
print(f"  Database: {'PostgreSQL' if DATABASE_URL else 'SQLite (local)'}")
print(f"  Frontend URL: {FRONTEND_URL}")
