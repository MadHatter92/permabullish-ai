"""
Permabullish API - AI Stock Researcher
Generate institutional-quality equity research reports for Indian stocks.
"""

from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel
from typing import Optional
import json
import hashlib
import os
from pathlib import Path

from authlib.integrations.starlette_client import OAuth
from starlette.middleware.sessions import SessionMiddleware

import database as db
import auth
from yahoo_finance import fetch_stock_data, search_stocks
from report_generator import generate_ai_analysis, generate_report_html
from config import (
    SECRET_KEY, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET,
    GOOGLE_REDIRECT_URI, FRONTEND_URL, CORS_ORIGINS, ENVIRONMENT,
    SUBSCRIPTION_TIERS
)

# Initialize FastAPI app
app = FastAPI(
    title="Permabullish API",
    description="AI-powered equity research reports for Indian stocks",
    version="2.0.0"
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session middleware for OAuth state management
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

# Configure OAuth
oauth = OAuth()
if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
    oauth.register(
        name='google',
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'}
    )

# Mount static files for frontend (local development)
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database tables on application startup."""
    db.init_database()


# Request/Response Models
class UserRegister(BaseModel):
    email: str
    password: str
    full_name: str


class UserLogin(BaseModel):
    email: str
    password: str


class GenerateReportRequest(BaseModel):
    symbol: str
    exchange: str = "NSE"
    force_regenerate: bool = False  # Force regeneration even if cached


class WatchlistAddRequest(BaseModel):
    ticker: str
    exchange: str = "NSE"
    company_name: Optional[str] = None


class UserTargetPriceRequest(BaseModel):
    report_cache_id: int
    target_price: float


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class MessageResponse(BaseModel):
    message: str
    success: bool = True


# Health check
@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Permabullish API",
        "environment": ENVIRONMENT,
        "version": "2.0.0"
    }


# Admin endpoint to reset usage (for testing)
@app.post("/api/admin/reset-usage/{email}")
async def reset_user_usage(email: str, secret: str = ""):
    """Reset a user's usage count for testing. Requires admin secret."""
    # Simple security - require a secret key
    admin_secret = os.getenv("ADMIN_SECRET", "permabullish-test-2024")
    if secret != admin_secret:
        raise HTTPException(status_code=403, detail="Invalid admin secret")

    user = db.get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=404, detail=f"User {email} not found")

    # Reset usage for current month
    db.reset_user_usage(user["id"])

    return {"message": f"Usage reset for {email}", "success": True}


# Auth Routes
@app.post("/api/auth/register", response_model=TokenResponse)
async def register(user_data: UserRegister):
    """Register a new user."""
    success, message, user = auth.register_user(
        email=user_data.email,
        password=user_data.password,
        full_name=user_data.full_name
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )

    # Auto-login after registration
    _, _, token = auth.authenticate_user(user_data.email, user_data.password)

    return TokenResponse(
        access_token=token,
        user={
            "id": user["id"],
            "email": user["email"],
            "full_name": user["full_name"],
            "subscription_tier": user.get("subscription_tier", "free")
        }
    )


@app.post("/api/auth/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    """Login and get access token."""
    success, message, token = auth.authenticate_user(
        email=credentials.email,
        password=credentials.password
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=message
        )

    user = db.get_user_by_email(credentials.email)

    return TokenResponse(
        access_token=token,
        user={
            "id": user["id"],
            "email": user["email"],
            "full_name": user["full_name"],
            "subscription_tier": user.get("subscription_tier", "free")
        }
    )


@app.get("/api/auth/me")
async def get_current_user_info(current_user: dict = Depends(auth.get_current_user)):
    """Get current logged-in user info."""
    return {
        "id": current_user["id"],
        "email": current_user["email"],
        "full_name": current_user["full_name"],
        "avatar_url": current_user.get("avatar_url"),
        "auth_provider": current_user.get("auth_provider", "local"),
        "subscription_tier": current_user.get("subscription_tier", "free"),
        "created_at": current_user["created_at"]
    }


# Google OAuth Routes
@app.get("/api/auth/google/login")
async def google_login(request: Request):
    """Initiate Google OAuth flow."""
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is not configured"
        )
    return await oauth.google.authorize_redirect(request, GOOGLE_REDIRECT_URI)


@app.get("/api/auth/google/callback")
async def google_callback(request: Request):
    """Handle Google OAuth callback."""
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is not configured"
        )

    try:
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get('userinfo')

        if not user_info:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get user info from Google"
            )

        # Get or create user in database
        user = db.get_or_create_google_user(
            google_id=user_info['sub'],
            email=user_info['email'],
            full_name=user_info.get('name', user_info.get('email', '')),
            avatar_url=user_info.get('picture')
        )

        # Create JWT token
        access_token = auth.create_access_token(
            data={"sub": str(user["id"]), "email": user["email"]}
        )

        # Redirect to frontend with token
        redirect_url = f"{FRONTEND_URL}/dashboard.html?token={access_token}"
        return RedirectResponse(url=redirect_url)

    except Exception as e:
        # Redirect to frontend with error
        redirect_url = f"{FRONTEND_URL}/index.html?error=auth_failed"
        return RedirectResponse(url=redirect_url)


# Helper function for anonymous user identification
def get_client_identifier(request: Request) -> str:
    """Get a hashed identifier for anonymous users based on IP."""
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
    else:
        client_ip = request.client.host if request.client else "unknown"

    return hashlib.sha256(client_ip.encode()).hexdigest()[:32]


# Usage Routes
@app.get("/api/usage")
async def get_usage_stats(current_user: dict = Depends(auth.get_current_user)):
    """Get user's current month usage statistics."""
    usage = db.get_usage(current_user["id"])
    return usage


@app.get("/api/usage/anonymous")
async def get_anonymous_usage_stats(request: Request):
    """Get anonymous user's usage statistics."""
    identifier = get_client_identifier(request)
    usage = db.get_anonymous_usage(identifier)
    return usage


# Stock Search Routes
@app.get("/api/stocks/search")
async def search_indian_stocks(
    q: str,
    limit: int = 10
):
    """Search for Indian stocks by name or symbol."""
    if len(q) < 1:
        return []

    results = search_stocks(q, limit=limit)
    return results


@app.get("/api/stocks/{symbol}")
async def get_stock_info(
    symbol: str,
    exchange: str = "NSE"
):
    """Get basic stock information (preview before generating report)."""
    stock_data = fetch_stock_data(symbol, exchange)

    if not stock_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stock {symbol} not found on {exchange}"
        )

    basic = stock_data.get("basic_info", {})
    price = stock_data.get("price_info", {})
    valuation = stock_data.get("valuation", {})

    return {
        "symbol": basic.get("ticker", symbol),
        "company_name": basic.get("company_name", ""),
        "sector": basic.get("sector", ""),
        "industry": basic.get("industry", ""),
        "current_price": price.get("current_price", 0),
        "market_cap": valuation.get("market_cap", 0),
        "pe_ratio": valuation.get("pe_ratio", 0),
    }


# Report Generation Routes (Stock Research)
@app.post("/api/reports/generate")
async def generate_report(
    request: Request,
    report_request: GenerateReportRequest,
    current_user: Optional[dict] = Depends(auth.get_optional_current_user)
):
    """Generate or retrieve a cached equity research report."""
    ticker = report_request.symbol.upper()
    exchange = report_request.exchange.upper()

    # Check for cached report first
    cached_report = db.get_cached_report(ticker, exchange)
    user_id = current_user["id"] if current_user else None
    is_anonymous = current_user is None

    # Determine if we need to generate a new report
    need_generation = False

    if cached_report is None:
        # No cached report exists
        need_generation = True
    elif report_request.force_regenerate:
        # User explicitly requested regeneration
        need_generation = True
    elif cached_report.get('is_outdated', False):
        # Report is older than 15 days
        if current_user:
            # Check if user has viewed this report before
            if not db.has_user_viewed_report(user_id, ticker, exchange):
                # First-time viewer + outdated = auto-regenerate
                need_generation = True
            # else: returning viewer + outdated = show cached (they can manually regenerate)

    # If we need to generate, check usage limits first
    if need_generation:
        if current_user:
            if not db.can_generate_report(user_id):
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Monthly report limit reached. Limit resets on the 1st of next month."
                )
        else:
            identifier = get_client_identifier(request)
            if not db.can_anonymous_generate(identifier):
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Free report limit reached (3 reports). Please sign in for more reports."
                )

        # Fetch stock data and generate report
        stock_data = fetch_stock_data(ticker, exchange)

        if not stock_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Stock {ticker} not found on {exchange}"
            )

        # Generate AI analysis
        analysis = generate_ai_analysis(stock_data)

        # Generate HTML report
        report_html = generate_report_html(stock_data, analysis)

        # Extract key info for storage
        basic = stock_data.get("basic_info", {})
        price = stock_data.get("price_info", {})

        # Save to cache (shared across all users)
        report_cache_id = db.save_cached_report(
            ticker=ticker,
            exchange=exchange,
            company_name=basic.get("company_name", ticker),
            sector=basic.get("sector", ""),
            current_price=price.get("current_price", 0),
            ai_target_price=analysis.get("target_price", 0),
            recommendation=analysis.get("recommendation", "HOLD"),
            report_html=report_html,
            report_data=json.dumps({"stock_data": stock_data, "analysis": analysis})
        )

        # Increment usage
        if is_anonymous:
            db.increment_anonymous_usage(get_client_identifier(request))
        else:
            db.increment_usage(user_id)

        # Get the updated cached report
        cached_report = db.get_cached_report_by_id(report_cache_id)
        generated_new = True
    else:
        report_cache_id = cached_report['id']
        generated_new = False

    # Link user to report (for authenticated users)
    if current_user:
        db.link_user_to_report(user_id, report_cache_id)

    return {
        "report_cache_id": report_cache_id,
        "company_name": cached_report.get("company_name", ""),
        "ticker": ticker,
        "exchange": exchange,
        "recommendation": cached_report.get("recommendation", "HOLD"),
        "ai_target_price": cached_report.get("ai_target_price", 0),
        "current_price": cached_report.get("current_price", 0),
        "generated_at": str(cached_report.get("generated_at", "")),
        "is_outdated": cached_report.get("is_outdated", False),
        "generated_new": generated_new
    }


@app.get("/api/reports")
async def get_user_reports(
    limit: int = 50,
    current_user: dict = Depends(auth.get_current_user)
):
    """Get report history for authenticated user (with freshness info)."""
    reports = db.get_user_report_history(current_user["id"], limit=limit)
    return reports


@app.get("/api/reports/cached/{ticker}")
async def get_cached_report_by_ticker(
    ticker: str,
    exchange: str = "NSE"
):
    """Get a cached report by ticker (if exists)."""
    report = db.get_cached_report(ticker.upper(), exchange.upper())

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No cached report for {ticker} on {exchange}"
        )

    return report


@app.get("/api/reports/{report_cache_id}")
async def get_report(
    report_cache_id: int,
    current_user: Optional[dict] = Depends(auth.get_optional_current_user)
):
    """Get a specific cached report by ID."""
    report = db.get_cached_report_by_id(report_cache_id)

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found"
        )

    # If authenticated, link user to report (tracks viewing) and get user's target price
    if current_user:
        db.link_user_to_report(current_user["id"], report_cache_id)
        user_target = db.get_user_target_price(current_user["id"], report_cache_id)
        if user_target:
            report["user_target_price"] = user_target

    return report


@app.get("/api/reports/{report_cache_id}/html", response_class=HTMLResponse)
async def get_report_html(
    report_cache_id: int,
    current_user: Optional[dict] = Depends(auth.get_optional_current_user)
):
    """Get the HTML content of a cached report for viewing."""
    report = db.get_cached_report_by_id(report_cache_id)

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found"
        )

    # If authenticated, link user to report (tracks viewing)
    if current_user:
        db.link_user_to_report(current_user["id"], report_cache_id)

    return HTMLResponse(content=report["report_html"])


# ============================================
# User Target Price
# ============================================

@app.put("/api/user/target-price")
async def set_user_target_price(
    request_data: UserTargetPriceRequest,
    current_user: dict = Depends(auth.get_current_user)
):
    """Set user's personal target price for a stock."""
    success = db.update_user_target_price(
        current_user["id"],
        request_data.report_cache_id,
        request_data.target_price
    )

    if not success:
        # User hasn't viewed this report yet, link them first
        db.link_user_to_report(current_user["id"], request_data.report_cache_id, request_data.target_price)

    return {"message": "Target price updated", "target_price": request_data.target_price}


# ============================================
# Watchlist Routes
# ============================================

@app.get("/api/watchlist")
async def get_watchlist(current_user: dict = Depends(auth.get_current_user)):
    """Get user's watchlist with report availability."""
    watchlist = db.get_watchlist(current_user["id"])
    return watchlist


@app.post("/api/watchlist")
async def add_to_watchlist(
    item: WatchlistAddRequest,
    current_user: dict = Depends(auth.get_current_user)
):
    """Add a stock to user's watchlist."""
    watchlist_id = db.add_to_watchlist(
        current_user["id"],
        item.ticker,
        item.exchange,
        item.company_name
    )

    if watchlist_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Stock already in watchlist"
        )

    return {"message": "Added to watchlist", "id": watchlist_id}


@app.delete("/api/watchlist/{ticker}")
async def remove_from_watchlist(
    ticker: str,
    exchange: str = "NSE",
    current_user: dict = Depends(auth.get_current_user)
):
    """Remove a stock from user's watchlist."""
    removed = db.remove_from_watchlist(current_user["id"], ticker, exchange)

    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stock not in watchlist"
        )

    return {"message": "Removed from watchlist"}


@app.get("/api/watchlist/check/{ticker}")
async def check_watchlist(
    ticker: str,
    exchange: str = "NSE",
    current_user: dict = Depends(auth.get_current_user)
):
    """Check if a stock is in user's watchlist."""
    is_watched = db.is_in_watchlist(current_user["id"], ticker, exchange)
    return {"in_watchlist": is_watched}


# ============================================
# Usage & Subscription Routes
# ============================================

@app.get("/api/usage")
async def get_usage(current_user: dict = Depends(auth.get_current_user)):
    """Get user's current usage stats based on their subscription tier."""
    usage = db.get_usage(current_user["id"])
    return usage


@app.get("/api/subscription/status")
async def get_subscription_status(current_user: dict = Depends(auth.get_current_user)):
    """Get detailed subscription status for the current user."""
    status = db.get_subscription_status(current_user["id"])
    return status


@app.get("/api/subscription/plans")
async def get_subscription_plans():
    """Get available subscription plans with pricing."""
    plans = []
    for tier_key, tier_data in SUBSCRIPTION_TIERS.items():
        plans.append({
            "id": tier_key,
            "name": tier_data.get("name", tier_key.title()),
            "description": tier_data.get("description", ""),
            "reports_limit": tier_data.get("reports_limit"),
            "is_lifetime": tier_data.get("is_lifetime", False),
            "pricing": {
                "monthly": tier_data.get("price_monthly"),
                "6_months": tier_data.get("price_6months"),
                "yearly": tier_data.get("price_yearly"),
            },
            "features": tier_data.get("features", {}),
        })
    return {"plans": plans}


@app.post("/api/subscription/checkout")
async def initiate_checkout(
    tier: str,
    period: int = 1,  # 1, 6, or 12 months
    current_user: dict = Depends(auth.get_current_user)
):
    """
    Initiate subscription checkout (placeholder for Cashfree integration).
    In production, this will create a Cashfree payment session.
    For now, returns a mock checkout URL.
    """
    if tier not in SUBSCRIPTION_TIERS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid tier: {tier}"
        )

    tier_config = SUBSCRIPTION_TIERS[tier]

    if tier == "free":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot purchase free tier"
        )

    if tier == "enterprise":
        return {
            "type": "contact",
            "message": "Please contact us for Enterprise pricing",
            "email": "enterprise@permabullish.com"
        }

    # Determine price based on period
    if period == 1:
        amount = tier_config.get("price_monthly", 0)
    elif period == 6:
        amount = tier_config.get("price_6months", 0)
    elif period == 12:
        amount = tier_config.get("price_yearly", 0)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid period. Must be 1, 6, or 12 months"
        )

    # Mock checkout response (will be replaced with Cashfree in Phase 3)
    order_id = f"order_{current_user['id']}_{tier}_{period}m_{int(datetime.now().timestamp())}"

    return {
        "type": "checkout",
        "order_id": order_id,
        "tier": tier,
        "tier_name": tier_config.get("name"),
        "period_months": period,
        "amount": amount,
        "currency": "INR",
        # Mock checkout URL - will be replaced with actual Cashfree URL
        "checkout_url": f"{FRONTEND_URL}/checkout.html?order_id={order_id}&tier={tier}&period={period}&amount={amount}",
        "message": "Redirect user to checkout_url to complete payment"
    }


@app.post("/api/subscription/activate")
async def activate_subscription(
    tier: str,
    period: int,
    payment_id: str = "mock_payment",
    current_user: dict = Depends(auth.get_current_user)
):
    """
    Activate subscription after successful payment (mock for testing).
    In production, this will be called by the Cashfree webhook.
    """
    if tier not in SUBSCRIPTION_TIERS or tier in ["free", "enterprise"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid tier: {tier}"
        )

    tier_config = SUBSCRIPTION_TIERS[tier]

    # Determine amount
    if period == 1:
        amount = tier_config.get("price_monthly", 0)
    elif period == 6:
        amount = tier_config.get("price_6months", 0)
    elif period == 12:
        amount = tier_config.get("price_yearly", 0)
    else:
        amount = 0

    # Create subscription record
    subscription_id = db.create_subscription_record(
        user_id=current_user["id"],
        tier=tier,
        period_months=period,
        amount_paid=amount,
        payment_id=payment_id
    )

    return {
        "message": f"Subscription activated: {tier_config.get('name')}",
        "subscription_id": subscription_id,
        "tier": tier,
        "period_months": period
    }


# Import datetime for order_id generation
from datetime import datetime


# Future: Cashfree webhook endpoint (placeholder for Phase 3)
@app.post("/api/webhooks/cashfree")
async def cashfree_webhook(request: Request):
    """Handle Cashfree payment webhook events (placeholder for future implementation)."""
    # TODO: Implement Cashfree webhook handling in Phase 3
    return {"status": "received"}


# Root redirect
@app.get("/")
async def root():
    """API root - redirect to docs or return info."""
    return {
        "message": "Welcome to Permabullish API",
        "version": "1.0.0",
        "docs": "/docs",
        "environment": ENVIRONMENT
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
