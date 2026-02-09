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
MONTHLY_REPORT_LIMIT = int(os.getenv("MONTHLY_REPORT_LIMIT", "50"))

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

# Resend Email Service
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")

# Featured report IDs for emails - rotated daily for variety
FEATURED_REPORT_IDS = [71, 92, 89, 90, 91, 38, 35, 88]

# Report freshness threshold (days)
REPORT_FRESHNESS_DAYS = 15

# Subscription Tiers with Pricing (prices in INR)
# Note: Authentication is required for report generation
SUBSCRIPTION_TIERS = {
    "free": {
        "name": "Free",
        "reports_limit": 5,  # Logged-in free users get 5 reports lifetime
        "is_lifetime": True,  # Free tier is lifetime limit, not monthly
        "price_monthly": 0,
        "price_6months": 0,
        "price_yearly": 0,
        "features": {
            "stock_research": True,
            "watchlist": True,
        },
        "description": "Try out AI stock research"
    },
    "basic": {
        "name": "Basic",
        "reports_limit": 50,
        "is_lifetime": False,  # Monthly limit
        "price_monthly": 999,
        "price_6months": 3999,   # 33% off (₹667/month)
        "price_yearly": 7499,    # 38% off (₹625/month)
        "struck_6months": 6000,  # Display struck price
        "struck_yearly": 12000,
        "features": {
            "stock_research": True,
            "watchlist": True,
        },
        "description": "For regular investors"
    },
    "pro": {
        "name": "Pro",
        "reports_limit": 100,
        "is_lifetime": False,
        "price_monthly": 1499,
        "price_6months": 5999,   # 33% off (₹1,000/month)
        "price_yearly": 9999,    # 44% off (₹833/month)
        "struck_6months": 9000,  # Display struck price
        "struck_yearly": 18000,
        "features": {
            "stock_research": True,
            "watchlist": True,
            "priority_generation": True,
        },
        "description": "For active traders"
    },
    "enterprise": {
        "name": "Enterprise",
        "reports_limit": 10000,  # Effectively unlimited
        "is_lifetime": False,
        "price_monthly": None,  # Contact us
        "price_6months": None,
        "price_yearly": None,
        "features": {
            "stock_research": True,
            "watchlist": True,
            "priority_generation": True,
            "api_access": True,
            "dedicated_support": True,
        },
        "description": "For institutions & advisors"
    }
}

print(f"Permabullish API Configuration:")
print(f"  Environment: {ENVIRONMENT}")
print(f"  Database: {'PostgreSQL' if DATABASE_URL else 'SQLite (local)'}")
print(f"  Frontend URL: {FRONTEND_URL}")
