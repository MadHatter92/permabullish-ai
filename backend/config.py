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

# CORS Origins
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8000",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8000",
]

if IS_PRODUCTION:
    CORS_ORIGINS.extend([
        "https://permabullish.com",
        "https://www.permabullish.com",
        "https://api.permabullish.com",
    ])
elif IS_STAGING:
    CORS_ORIGINS.extend([
        "https://permabullish-web-staging.onrender.com",
        "https://permabullish-api-staging.onrender.com",
    ])

# Add FRONTEND_URL to allowed origins if it's not already there
if FRONTEND_URL and FRONTEND_URL not in CORS_ORIGINS:
    CORS_ORIGINS.append(FRONTEND_URL)

# Stripe Configuration (for future paywall)
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
STRIPE_PRICE_PRO_MONTHLY = os.getenv("STRIPE_PRICE_PRO_MONTHLY", "")  # Stripe Price ID
STRIPE_PRICE_ENTERPRISE_MONTHLY = os.getenv("STRIPE_PRICE_ENTERPRISE_MONTHLY", "")

# Subscription Tiers
SUBSCRIPTION_TIERS = {
    "free": {
        "monthly_reports": 20,
        "features": {
            "stock_research": True,
            "mf_analytics": False,
            "pms_tracker": False,
            "api_access": False,
        }
    },
    "pro": {
        "monthly_reports": 100,
        "features": {
            "stock_research": True,
            "mf_analytics": True,
            "pms_tracker": True,
            "api_access": False,
        }
    },
    "enterprise": {
        "monthly_reports": 1000,
        "features": {
            "stock_research": True,
            "mf_analytics": True,
            "pms_tracker": True,
            "api_access": True,
        }
    }
}

print(f"Permabullish API Configuration:")
print(f"  Environment: {ENVIRONMENT}")
print(f"  Database: {'PostgreSQL' if DATABASE_URL else 'SQLite (local)'}")
print(f"  Frontend URL: {FRONTEND_URL}")
