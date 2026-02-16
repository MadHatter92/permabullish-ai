"""
Permabullish API - AI Stock Researcher
Generate institutional-quality equity research reports for Indian stocks.
"""

from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from pydantic import BaseModel
from typing import Optional
import json
import logging
import os
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("permabullish")

from authlib.integrations.starlette_client import OAuth
from starlette.middleware.sessions import SessionMiddleware

# Rate limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

import database as db
import auth
from yahoo_finance import fetch_stock_data, search_stocks, fetch_chart_data
from report_generator import generate_ai_analysis, generate_report_html, generate_comparison_analysis
from config import (
    SECRET_KEY, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET,
    GOOGLE_REDIRECT_URI, FRONTEND_URL, CORS_ORIGINS, ENVIRONMENT,
    SUBSCRIPTION_TIERS, CASHFREE_APP_ID, CASHFREE_SECRET_KEY,
    FEATURED_REPORT_IDS
)
import cashfree
import share_card

# Error tracking (Sentry)
import sentry_sdk
SENTRY_DSN = os.getenv("SENTRY_DSN", "")
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=ENVIRONMENT,
        traces_sample_rate=0.1,  # 10% of requests for performance monitoring
        send_default_pii=False,  # Don't send personally identifiable info
    )
    logger.info(f"Sentry initialized for {ENVIRONMENT} environment")

# Initialize FastAPI app
app = FastAPI(
    title="Permabullish API",
    description="AI-powered equity research reports for Indian stocks",
    version="2.0.0",
    # Disable Swagger UI in production (security)
    docs_url=None if ENVIRONMENT == "production" else "/docs",
    redoc_url=None if ENVIRONMENT == "production" else "/redoc",
    openapi_url=None if ENVIRONMENT == "production" else "/openapi.json",
)

# GZip compression for API responses (minimum 500 bytes to compress)
app.add_middleware(GZipMiddleware, minimum_size=500)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session middleware for OAuth state management
# Configure with proper cookie settings for OAuth cross-site flows
app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    same_site="lax",  # Allow OAuth redirects while maintaining some CSRF protection
    https_only=ENVIRONMENT != "development",  # Secure cookies in production/staging
)

# Rate limiting setup
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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
    signup_source: str = ""


class UserLogin(BaseModel):
    email: str
    password: str


class GenerateReportRequest(BaseModel):
    symbol: str
    exchange: str = "NSE"
    force_regenerate: bool = False  # Force regeneration even if cached
    language: str = "en"  # Language: 'en' (English), 'hi' (Hindi), 'gu' (Gujarati), 'kn' (Kannada)


class WatchlistAddRequest(BaseModel):
    ticker: str
    exchange: str = "NSE"
    company_name: Optional[str] = None


class CompareRequest(BaseModel):
    stock_a: str
    stock_b: str
    exchange_a: str = "NSE"
    exchange_b: str = "NSE"
    language: str = "en"


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


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class ResendVerificationRequest(BaseModel):
    email: str


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


@app.get("/api/qr")
async def generate_qr(
    utm_source: str = "",
    utm_medium: str = "",
    utm_campaign: str = "",
    utm_content: str = ""
):
    """Generate a branded QR code pointing to permabullish.com with UTM params."""
    import qrcode
    from qrcode.image.styledpil import StyledPilImage
    from qrcode.image.styles.colormasks import SolidFillColorMask
    import io

    # Build URL with UTM params
    base_url = "https://permabullish.com/"
    params = {}
    if utm_source: params["utm_source"] = utm_source
    if utm_medium: params["utm_medium"] = utm_medium
    if utm_campaign: params["utm_campaign"] = utm_campaign
    if utm_content: params["utm_content"] = utm_content

    if params:
        from urllib.parse import urlencode
        base_url += "?" + urlencode(params)

    # Generate QR code with brand colors
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=10, border=2)
    qr.add_data(base_url)
    qr.make(fit=True)

    # Navy foreground (#102a43), white background
    img = qr.make_image(
        image_factory=StyledPilImage,
        color_mask=SolidFillColorMask(
            back_color=(255, 255, 255),
            front_color=(16, 42, 67)
        )
    )

    # Return as PNG
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    return Response(content=buffer.getvalue(), media_type="image/png")


# Unsubscribe endpoint (no auth required)
class UnsubscribeRequest(BaseModel):
    email: str


@app.post("/api/unsubscribe")
async def unsubscribe_email(request: UnsubscribeRequest):
    """
    Unsubscribe an email from marketing emails.
    Works for both registered users and external contacts.
    """
    email = request.email.lower().strip()

    if not email:
        raise HTTPException(status_code=400, detail="Email is required")

    # Try to unsubscribe from external contacts first
    external_result = db.unsubscribe_external_contact(email)

    # Also try to mark user as unsubscribed if they're a registered user
    user_result = db.unsubscribe_user(email)

    if external_result or user_result:
        already_unsubscribed = (
            (external_result and external_result.get('already_unsubscribed')) and
            (not user_result or user_result.get('already_unsubscribed'))
        )
        return {
            "success": True,
            "message": "Successfully unsubscribed",
            "already_unsubscribed": already_unsubscribed
        }
    else:
        # Email not found in either table - still return success
        # (don't reveal if email exists or not)
        return {
            "success": True,
            "message": "Successfully unsubscribed",
            "already_unsubscribed": False
        }


@app.get("/api/sentry-test")
async def sentry_test(secret: str = ""):
    """Test endpoint to verify Sentry is working. Requires admin secret."""
    admin_secret = os.getenv("ADMIN_SECRET", "")
    if not admin_secret or secret != admin_secret:
        raise HTTPException(status_code=403, detail="Invalid admin secret")
    # This will trigger a Sentry error
    raise Exception("Sentry test error - if you see this in Sentry, it's working!")


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


# Admin endpoint to reset provider rate limits
@app.post("/api/admin/reset-rate-limits")
async def reset_rate_limits(secret: str = ""):
    """Reset all stock data provider rate limits. Requires admin secret."""
    admin_secret = os.getenv("ADMIN_SECRET", "permabullish-test-2024")
    if secret != admin_secret:
        raise HTTPException(status_code=403, detail="Invalid admin secret")

    from yahoo_finance import stock_manager
    stock_manager.reset_rate_limits()

    return {
        "message": "All provider rate limits reset",
        "providers": stock_manager.get_provider_status()
    }


# Admin endpoint to check provider status
@app.get("/api/admin/provider-status")
async def get_provider_status(secret: str = ""):
    """Get status of all stock data providers. Requires admin secret."""
    admin_secret = os.getenv("ADMIN_SECRET", "permabullish-test-2024")
    if secret != admin_secret:
        raise HTTPException(status_code=403, detail="Invalid admin secret")

    from yahoo_finance import stock_manager
    return {"providers": stock_manager.get_provider_status()}


class AdminSubscriptionRequest(BaseModel):
    email: str
    tier: str  # basic, pro, enterprise
    period_months: int = 12  # Duration in months
    amount_paid: float = 0  # For record keeping (0 for comped/enterprise)
    note: str = ""  # Optional note (e.g., "Enterprise client - Company XYZ")


@app.post("/api/admin/set-subscription")
async def admin_set_subscription(request_data: AdminSubscriptionRequest, secret: str = ""):
    """
    Manually set a user's subscription. For enterprise clients or manual adjustments.
    Requires admin secret.
    """
    admin_secret = os.getenv("ADMIN_SECRET", "permabullish-test-2024")
    if secret != admin_secret:
        raise HTTPException(status_code=403, detail="Invalid admin secret")

    # Validate tier
    valid_tiers = ["free", "basic", "pro", "enterprise"]
    if request_data.tier not in valid_tiers:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid tier. Must be one of: {valid_tiers}"
        )

    # Find user by email
    user = db.get_user_by_email(request_data.email)
    if not user:
        raise HTTPException(status_code=404, detail=f"User not found: {request_data.email}")

    # Create subscription record
    subscription_id = db.create_subscription_record(
        user_id=user["id"],
        tier=request_data.tier,
        period_months=request_data.period_months,
        amount_paid=request_data.amount_paid,
        payment_id=f"admin_{request_data.note}" if request_data.note else "admin_manual"
    )

    # Get updated subscription status
    status = db.get_subscription_status(user["id"])

    return {
        "success": True,
        "message": f"Subscription set for {request_data.email}",
        "user_id": user["id"],
        "subscription_id": subscription_id,
        "tier": request_data.tier,
        "period_months": request_data.period_months,
        "expires_at": status.get("expires_at") if status else None
    }


@app.get("/api/admin/user-info/{email}")
async def admin_get_user_info(email: str, secret: str = ""):
    """Get user info and subscription status. Requires admin secret."""
    admin_secret = os.getenv("ADMIN_SECRET", "permabullish-test-2024")
    if secret != admin_secret:
        raise HTTPException(status_code=403, detail="Invalid admin secret")

    user = db.get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=404, detail=f"User not found: {email}")

    subscription = db.get_subscription_status(user["id"])
    usage = db.get_usage(user["id"])

    return {
        "user": {
            "id": user["id"],
            "email": user["email"],
            "name": user.get("name"),
            "created_at": user.get("created_at")
        },
        "subscription": subscription,
        "usage": usage
    }


# Auth Routes
@app.post("/api/auth/register")
@limiter.limit("3/minute")
async def register(request: Request, user_data: UserRegister):
    """Register a new user. Sends verification email. Rate limited: 3/minute."""
    success, message, user = auth.register_user(
        email=user_data.email,
        password=user_data.password,
        full_name=user_data.full_name,
        signup_source=user_data.signup_source
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )

    # Send verification email instead of auto-login
    try:
        from email_service import send_verification_email, get_first_name
        verification_token = auth.create_verification_token(user["id"], user["email"])
        # Link directly to backend API which handles verification and redirects to frontend
        api_base = str(request.base_url).rstrip('/') + "/api"
        verification_url = f"{api_base}/auth/verify-email?token={verification_token}"
        first_name = get_first_name(user["full_name"])
        send_verification_email(user["email"], first_name, verification_url)
    except Exception as e:
        logger.error(f"Failed to send verification email to {user['email']}: {e}")

    return {
        "message": "Please check your email to verify your account",
        "email": user["email"]
    }


@app.post("/api/auth/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(request: Request, credentials: UserLogin):
    """Login and get access token. Rate limited: 5/minute."""
    success, message, token = auth.authenticate_user(
        email=credentials.email,
        password=credentials.password
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=message
        )

    user = db.get_user_by_email(credentials.email.lower().strip())

    return TokenResponse(
        access_token=token,
        user={
            "id": user["id"],
            "email": user["email"],
            "full_name": user["full_name"],
            "subscription_tier": user.get("subscription_tier", "free")
        }
    )


@app.get("/api/auth/verify-email")
async def verify_email(token: str):
    """Verify user's email address from the link sent to their inbox."""
    import urllib.parse

    payload = auth.decode_purpose_token(token, "email_verify")

    if not payload:
        msg = urllib.parse.quote("Invalid or expired verification link")
        return RedirectResponse(
            url=f"{FRONTEND_URL}/verify-email.html?status=error&message={msg}",
            status_code=302
        )

    user_id = int(payload["sub"])
    user = db.get_user_by_id(user_id)

    if not user:
        msg = urllib.parse.quote("User not found")
        return RedirectResponse(
            url=f"{FRONTEND_URL}/verify-email.html?status=error&message={msg}",
            status_code=302
        )

    if user.get("email_verified"):
        return RedirectResponse(
            url=f"{FRONTEND_URL}/verify-email.html?status=success&message=Email already verified",
            status_code=302
        )

    # Mark email as verified
    db.mark_email_verified(user_id)

    # Now send welcome email (post-verification)
    try:
        from email_service import send_welcome_email, get_featured_reports_for_email, get_first_name
        from datetime import datetime
        sample_reports = get_featured_reports_for_email(datetime.now().timetuple().tm_yday)
        first_name = get_first_name(user.get("full_name", ""))
        if send_welcome_email(user["email"], first_name, sample_reports):
            db.mark_welcome_email_sent(user_id)
    except Exception as e:
        logger.error(f"Failed to send welcome email to {user['email']}: {e}")

    return RedirectResponse(
        url=f"{FRONTEND_URL}/verify-email.html?status=success",
        status_code=302
    )


@app.post("/api/auth/resend-verification")
@limiter.limit("3/minute")
async def resend_verification(request: Request, data: ResendVerificationRequest):
    """Resend verification email. Rate limited: 3/minute."""
    email = data.email.lower().strip()

    # Always return success (don't reveal if email exists)
    user = db.get_user_by_email(email)
    if user and not user.get("email_verified", False):
        try:
            from email_service import send_verification_email, get_first_name
            verification_token = auth.create_verification_token(user["id"], user["email"])
            api_base = str(request.base_url).rstrip('/') + "/api"
            verification_url = f"{api_base}/auth/verify-email?token={verification_token}"
            first_name = get_first_name(user.get("full_name", ""))
            send_verification_email(user["email"], first_name, verification_url)
        except Exception as e:
            logger.error(f"Failed to resend verification email to {email}: {e}")

    return {"message": "If an account exists with this email, a verification link has been sent."}


@app.post("/api/auth/forgot-password")
@limiter.limit("3/minute")
async def forgot_password(request: Request, data: ForgotPasswordRequest):
    """Send password reset email. Rate limited: 3/minute."""
    email = data.email.lower().strip()

    # Always return success (don't reveal if email exists)
    user = db.get_user_by_email(email)
    if user and user.get("password_hash"):
        # Only send reset email if user has a password (not Google-only)
        try:
            from email_service import send_password_reset_email, get_first_name
            reset_token = auth.create_password_reset_token(user["id"], user["email"])
            reset_url = f"{FRONTEND_URL.rstrip('/')}/reset-password.html?token={reset_token}"
            first_name = get_first_name(user.get("full_name", ""))
            send_password_reset_email(user["email"], first_name, reset_url)
        except Exception as e:
            logger.error(f"Failed to send password reset email to {email}: {e}")

    return {"message": "If an account exists with this email, a password reset link has been sent."}


@app.post("/api/auth/reset-password")
@limiter.limit("5/minute")
async def reset_password(request: Request, data: ResetPasswordRequest):
    """Reset password using a valid reset token. Rate limited: 5/minute."""
    payload = auth.decode_purpose_token(data.token, "password_reset")

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset link. Please request a new one."
        )

    if len(data.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters"
        )

    user_id = int(payload["sub"])
    user = db.get_user_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found"
        )

    # Update password
    new_hash = auth.get_password_hash(data.new_password)
    db.update_password_hash(user_id, new_hash)

    # Also mark email as verified if not already (they proved ownership via email)
    if not user.get("email_verified", False):
        db.mark_email_verified(user_id)

    return {"message": "Password has been reset successfully. You can now sign in."}


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
async def google_login(request: Request, signup_source: str = "", return_to: str = ""):
    """Initiate Google OAuth flow."""
    logger.info(f"OAuth login initiated. Redirect URI: {GOOGLE_REDIRECT_URI}")
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        logger.error("Google OAuth credentials not configured")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is not configured"
        )
    # Store signup_source in session so we can use it in the callback
    if signup_source:
        request.session["signup_source"] = signup_source
    # Store return_to path (must be relative) so callback can redirect back
    if return_to and return_to.startswith("/"):
        request.session["return_to"] = return_to
    return await oauth.google.authorize_redirect(request, GOOGLE_REDIRECT_URI)


@app.get("/api/auth/google/callback")
async def google_callback(request: Request):
    """Handle Google OAuth callback."""
    logger.info(f"OAuth callback received. FRONTEND_URL: {FRONTEND_URL}")

    # Debug: Check if session cookie is present
    session_cookie = request.cookies.get("session")
    logger.info(f"Session cookie present: {session_cookie is not None}")
    if request.session:
        logger.info(f"Session keys: {list(request.session.keys())}")
    else:
        logger.warning("Session is empty or not available")

    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        logger.error("Google OAuth not configured")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is not configured"
        )

    try:
        logger.info("Exchanging authorization code for token...")
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get('userinfo')
        logger.info(f"Got user info: {user_info.get('email') if user_info else 'None'}")

        if not user_info:
            logger.error("No user info in token response")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get user info from Google"
            )

        # Get or create user in database
        signup_source = request.session.pop("signup_source", "") or "google_oauth"
        user = db.get_or_create_google_user(
            google_id=user_info['sub'],
            email=user_info['email'],
            full_name=user_info.get('name', user_info.get('email', '')),
            avatar_url=user_info.get('picture'),
            signup_source=signup_source
        )
        logger.info(f"User authenticated: {user['email']}")

        # Create JWT token
        access_token = auth.create_access_token(
            data={"sub": str(user["id"]), "email": user["email"]}
        )

        # Check if user should be redirected back to a specific page (e.g. shared report)
        return_to = request.session.pop("return_to", "")
        if return_to and return_to.startswith("/"):
            # Append token as query param (handle existing query string)
            separator = "&" if "?" in return_to else "?"
            redirect_url = f"{FRONTEND_URL}{return_to}{separator}token={access_token}"
            logger.info(f"Redirecting to return_to={return_to} for user: {user['email']}")
        else:
            redirect_url = f"{FRONTEND_URL}/dashboard.html?token={access_token}"
            logger.info(f"Redirecting to dashboard for user: {user['email']}")
        return RedirectResponse(url=redirect_url, status_code=302)

    except Exception as e:
        # Log the error with full traceback
        logger.exception(f"OAuth callback error: {type(e).__name__}: {str(e)}")

        # Capture in Sentry if available
        if SENTRY_DSN:
            sentry_sdk.capture_exception(e)

        # Redirect to frontend with error
        redirect_url = f"{FRONTEND_URL}/index.html?error=auth_failed&message={str(e)[:100]}"
        return RedirectResponse(url=redirect_url, status_code=302)


# Usage Routes
@app.get("/api/usage")
async def get_usage_stats(current_user: dict = Depends(auth.get_current_user)):
    """Get user's current month usage statistics."""
    usage = db.get_usage(current_user["id"])
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


@app.get("/api/stocks/{symbol}/chart")
async def get_stock_chart(
    symbol: str,
    exchange: str = "NSE",
    period: str = "1y"
):
    """
    Get historical price data for stock charts.

    Args:
        symbol: Stock ticker symbol
        exchange: Exchange (NSE or BSE)
        period: Time period - 1m, 3m, 6m, 1y, 5y

    Returns:
        Chart data with price history, moving averages, and key stats
    """
    # Validate period
    valid_periods = ["1m", "3m", "6m", "1y", "5y"]
    if period not in valid_periods:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid period. Must be one of: {', '.join(valid_periods)}"
        )

    chart_data = fetch_chart_data(symbol, exchange, period)

    if not chart_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chart data not available for {symbol} on {exchange}"
        )

    return chart_data


# Report Generation Routes (Stock Research)
@app.post("/api/reports/generate")
@limiter.limit("10/hour")
async def generate_report(
    request: Request,
    report_request: GenerateReportRequest,
    current_user: dict = Depends(auth.get_current_user)
):
    """Generate or retrieve a cached equity research report. Requires authentication."""
    ticker = report_request.symbol.upper()
    exchange = report_request.exchange.upper()
    language = report_request.language.lower() if report_request.language else 'en'

    logger.info(f"Generate report request: {ticker}/{exchange}, language={language} (raw: {report_request.language})")

    # Validate language
    if language not in ['en', 'hi', 'gu', 'kn']:
        logger.warning(f"Invalid language '{language}', defaulting to 'en'")
        language = 'en'

    # Check for cached report first (language-specific)
    cached_report = db.get_cached_report(ticker, exchange, language)
    logger.info(f"Cached report found: {cached_report is not None}, cached language: {cached_report.get('language') if cached_report else 'N/A'}")
    user_id = current_user["id"]

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
        # Check if user has viewed this report before
        if not db.has_user_viewed_report(user_id, ticker, exchange):
            # First-time viewer + outdated = auto-regenerate
            need_generation = True
        # else: returning viewer + outdated = show cached (they can manually regenerate)

    # If we need to generate, check usage limits first
    if need_generation:
        if not db.can_generate_report(user_id):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Monthly report limit reached. Limit resets on the 1st of next month."
            )

        # Fetch stock data and generate report
        stock_data = fetch_stock_data(ticker, exchange)

        if not stock_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Stock {ticker} not found on {exchange}"
            )

        # Generate AI analysis (in selected language)
        analysis = generate_ai_analysis(stock_data, language)

        # Generate HTML report (with language-specific fonts)
        report_html = generate_report_html(stock_data, analysis, language)

        # Extract key info for storage
        basic = stock_data.get("basic_info", {})
        price = stock_data.get("price_info", {})

        # Extract token usage if available
        token_usage = analysis.get("_token_usage", {})

        # Save to cache (shared across all users, per language)
        report_cache_id = db.save_cached_report(
            ticker=ticker,
            exchange=exchange,
            company_name=basic.get("company_name", ticker),
            sector=basic.get("sector", ""),
            current_price=price.get("current_price", 0),
            ai_target_price=analysis.get("target_price", 0),
            recommendation=analysis.get("recommendation", "HOLD"),
            report_html=report_html,
            report_data=json.dumps({"stock_data": stock_data, "analysis": analysis}),
            input_tokens=token_usage.get("input_tokens", 0),
            output_tokens=token_usage.get("output_tokens", 0),
            total_tokens=token_usage.get("total_tokens", 0),
            language=language
        )

        # Increment usage
        db.increment_usage(user_id)

        # Get the updated cached report
        cached_report = db.get_cached_report_by_id(report_cache_id)
        generated_new = True
    else:
        report_cache_id = cached_report['id']
        generated_new = False

    # Link user to report and update activity
    db.link_user_to_report(user_id, report_cache_id)
    db.update_user_activity(user_id)

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
        "generated_new": generated_new,
        "language": cached_report.get("language", "en")
    }


@app.post("/api/reports/compare")
@limiter.limit("10/hour")
async def compare_stocks(
    request: Request,
    compare_request: CompareRequest,
    current_user: dict = Depends(auth.get_current_user)
):
    """Compare two stocks side-by-side with AI analysis. Requires authentication."""
    import asyncio
    from concurrent.futures import ThreadPoolExecutor

    ticker_a = compare_request.stock_a.upper()
    ticker_b = compare_request.stock_b.upper()
    exchange_a = compare_request.exchange_a.upper()
    exchange_b = compare_request.exchange_b.upper()
    language = compare_request.language.lower() if compare_request.language else 'en'

    logger.info(f"Compare request: {ticker_a}/{exchange_a} vs {ticker_b}/{exchange_b}, language={language}")

    # Validate: can't compare same stock
    if ticker_a == ticker_b and exchange_a == exchange_b:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot compare a stock with itself. Please select two different stocks."
        )

    # Check usage limits (comparison costs 1 credit)
    user_id = current_user["id"]

    if not db.can_generate_report(user_id):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Monthly report limit reached. Limit resets on the 1st of next month."
        )

    # Fetch stock data for both stocks in parallel
    with ThreadPoolExecutor(max_workers=2) as executor:
        future_a = executor.submit(fetch_stock_data, ticker_a, exchange_a)
        future_b = executor.submit(fetch_stock_data, ticker_b, exchange_b)
        stock_data_a = future_a.result()
        stock_data_b = future_b.result()

    if not stock_data_a:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stock {ticker_a} not found on {exchange_a}"
        )

    if not stock_data_b:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stock {ticker_b} not found on {exchange_b}"
        )

    # Check for cached reports and get analysis
    cached_a = db.get_cached_report(ticker_a, exchange_a, language)
    cached_b = db.get_cached_report(ticker_b, exchange_b, language)

    # Get or generate analysis for stock A
    if cached_a and not cached_a.get('is_outdated', False):
        try:
            report_data_a = cached_a.get('report_data', {})
            # Handle both string and dict (depending on DB driver)
            if isinstance(report_data_a, str):
                report_data_a = json.loads(report_data_a)
            analysis_a = report_data_a.get('analysis', {}) if report_data_a else {}
        except (json.JSONDecodeError, TypeError):
            analysis_a = generate_ai_analysis(stock_data_a, language)
    else:
        analysis_a = generate_ai_analysis(stock_data_a, language)

    # Get or generate analysis for stock B
    if cached_b and not cached_b.get('is_outdated', False):
        try:
            report_data_b = cached_b.get('report_data', {})
            # Handle both string and dict (depending on DB driver)
            if isinstance(report_data_b, str):
                report_data_b = json.loads(report_data_b)
            analysis_b = report_data_b.get('analysis', {}) if report_data_b else {}
        except (json.JSONDecodeError, TypeError):
            analysis_b = generate_ai_analysis(stock_data_b, language)
    else:
        analysis_b = generate_ai_analysis(stock_data_b, language)

    # Generate AI comparison
    ai_comparison = generate_comparison_analysis(
        stock_data_a, stock_data_b,
        analysis_a, analysis_b,
        language
    )

    # Deduct 1 credit
    db.increment_usage(user_id)
    db.update_user_activity(user_id)

    # Extract key info for response
    basic_a = stock_data_a.get("basic_info", {})
    basic_b = stock_data_b.get("basic_info", {})
    price_a = stock_data_a.get("price_info", {})
    price_b = stock_data_b.get("price_info", {})
    valuation_a = stock_data_a.get("valuation", {})
    valuation_b = stock_data_b.get("valuation", {})
    financials_a = stock_data_a.get("financials", {})
    financials_b = stock_data_b.get("financials", {})
    returns_a = stock_data_a.get("returns", {})
    returns_b = stock_data_b.get("returns", {})
    balance_a = stock_data_a.get("balance_sheet", {})
    balance_b = stock_data_b.get("balance_sheet", {})

    # Build metrics comparison
    def determine_better(val_a, val_b, lower_is_better=False):
        if val_a is None or val_b is None or val_a == 0 or val_b == 0:
            return "N/A"
        if lower_is_better:
            return "A" if val_a < val_b else "B" if val_b < val_a else "TIE"
        return "A" if val_a > val_b else "B" if val_b > val_a else "TIE"

    metrics_comparison = {
        "valuation": {
            "pe_ratio": {
                "stock_a": valuation_a.get("pe_ratio", 0),
                "stock_b": valuation_b.get("pe_ratio", 0),
                "better": determine_better(valuation_a.get("pe_ratio"), valuation_b.get("pe_ratio"), lower_is_better=True)
            },
            "pb_ratio": {
                "stock_a": valuation_a.get("pb_ratio", 0),
                "stock_b": valuation_b.get("pb_ratio", 0),
                "better": determine_better(valuation_a.get("pb_ratio"), valuation_b.get("pb_ratio"), lower_is_better=True)
            },
            "ev_to_ebitda": {
                "stock_a": valuation_a.get("ev_to_ebitda", 0),
                "stock_b": valuation_b.get("ev_to_ebitda", 0),
                "better": determine_better(valuation_a.get("ev_to_ebitda"), valuation_b.get("ev_to_ebitda"), lower_is_better=True)
            }
        },
        "growth": {
            "revenue_growth": {
                "stock_a": financials_a.get("revenue_growth", 0),
                "stock_b": financials_b.get("revenue_growth", 0),
                "better": determine_better(financials_a.get("revenue_growth"), financials_b.get("revenue_growth"))
            }
        },
        "quality": {
            "roe": {
                "stock_a": returns_a.get("roe", 0),
                "stock_b": returns_b.get("roe", 0),
                "better": determine_better(returns_a.get("roe"), returns_b.get("roe"))
            },
            "profit_margin": {
                "stock_a": financials_a.get("profit_margin", 0),
                "stock_b": financials_b.get("profit_margin", 0),
                "better": determine_better(financials_a.get("profit_margin"), financials_b.get("profit_margin"))
            },
            "debt_to_equity": {
                "stock_a": balance_a.get("debt_to_equity", 0),
                "stock_b": balance_b.get("debt_to_equity", 0),
                "better": determine_better(balance_a.get("debt_to_equity"), balance_b.get("debt_to_equity"), lower_is_better=True)
            }
        }
    }

    # Build the response
    response_data = {
        "stock_a": {
            "ticker": ticker_a,
            "exchange": exchange_a,
            "company_name": basic_a.get("company_name", ticker_a),
            "sector": basic_a.get("sector", ""),
            "current_price": price_a.get("current_price", 0),
            "recommendation": analysis_a.get("recommendation", "HOLD"),
            "target_price": analysis_a.get("target_price", 0),
            "bull_case": analysis_a.get("bull_case", []),
            "bear_case": analysis_a.get("bear_case", []),
            "metrics": {
                "pe": valuation_a.get("pe_ratio", 0),
                "pb": valuation_a.get("pb_ratio", 0),
                "roe": (returns_a.get("roe", 0) or 0) * 100,
                "profit_margin": (financials_a.get("profit_margin", 0) or 0) * 100,
                "debt_to_equity": balance_a.get("debt_to_equity", 0),
                "revenue_growth": (financials_a.get("revenue_growth", 0) or 0) * 100,
                "market_cap": valuation_a.get("market_cap", 0)
            },
            "report_cache_id": cached_a.get("id") if cached_a else None
        },
        "stock_b": {
            "ticker": ticker_b,
            "exchange": exchange_b,
            "company_name": basic_b.get("company_name", ticker_b),
            "sector": basic_b.get("sector", ""),
            "current_price": price_b.get("current_price", 0),
            "recommendation": analysis_b.get("recommendation", "HOLD"),
            "target_price": analysis_b.get("target_price", 0),
            "bull_case": analysis_b.get("bull_case", []),
            "bear_case": analysis_b.get("bear_case", []),
            "metrics": {
                "pe": valuation_b.get("pe_ratio", 0),
                "pb": valuation_b.get("pb_ratio", 0),
                "roe": (returns_b.get("roe", 0) or 0) * 100,
                "profit_margin": (financials_b.get("profit_margin", 0) or 0) * 100,
                "debt_to_equity": balance_b.get("debt_to_equity", 0),
                "revenue_growth": (financials_b.get("revenue_growth", 0) or 0) * 100,
                "market_cap": valuation_b.get("market_cap", 0)
            },
            "report_cache_id": cached_b.get("id") if cached_b else None
        },
        "ai_comparison": ai_comparison,
        "metrics_comparison": metrics_comparison,
        "language": language
    }

    # Save the comparison to database
    comparison_cache_id = db.save_comparison(
        ticker_a=ticker_a,
        exchange_a=exchange_a,
        ticker_b=ticker_b,
        exchange_b=exchange_b,
        verdict=ai_comparison.get("verdict", "EITHER"),
        verdict_stock=ai_comparison.get("verdict_stock", ""),
        conviction=ai_comparison.get("conviction", "MEDIUM"),
        one_line_verdict=ai_comparison.get("one_line_verdict", ""),
        comparison_data=response_data,
        language=language
    )

    # Link user to comparison if authenticated
    if user_id:
        db.link_user_to_comparison(user_id, comparison_cache_id)

    # Add comparison_cache_id to response
    response_data["comparison_cache_id"] = comparison_cache_id

    return response_data


@app.get("/api/reports")
async def get_user_reports(
    limit: int = 50,
    current_user: dict = Depends(auth.get_current_user)
):
    """Get report history for authenticated user (with freshness info)."""
    reports = db.get_user_report_history(current_user["id"], limit=limit)
    return reports


@app.get("/api/comparisons")
async def get_user_comparisons(
    limit: int = 50,
    current_user: dict = Depends(auth.get_current_user)
):
    """Get comparison history for authenticated user."""
    comparisons = db.get_user_comparison_history(current_user["id"], limit=limit)
    return comparisons


@app.get("/api/comparisons/{comparison_id}")
async def get_comparison_by_id(
    comparison_id: int,
    current_user: Optional[dict] = Depends(auth.get_optional_current_user)
):
    """Get a specific comparison by ID."""
    comparison = db.get_comparison_by_id(comparison_id)
    if not comparison:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comparison not found"
        )

    # Link user to comparison if authenticated
    if current_user:
        db.link_user_to_comparison(current_user["id"], comparison_id)

    return comparison


@app.get("/api/reports/featured")
async def get_featured_reports():
    """Get featured sample reports for new users to see."""
    reports = db.get_featured_reports_by_ids(FEATURED_REPORT_IDS)
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


@app.get("/api/reports/{report_cache_id}/view", response_class=HTMLResponse)
async def get_report_direct_view(report_cache_id: int):
    """
    Direct report view for in-app browsers (Telegram, Instagram, etc.)
    that have issues with iframes. Returns full HTML page with report embedded.
    """
    report = db.get_cached_report_by_id(report_cache_id)

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found"
        )

    report_html = report.get("report_html", "")
    company_name = report.get("company_name", report.get("ticker", "Report"))
    ticker = report.get("ticker", "")
    recommendation = report.get("recommendation", "HOLD").replace("_", " ").title()
    current_price = report.get("current_price", 0)
    target_price = report.get("ai_target_price", 0)

    # Calculate upside for OG description
    upside_text = ""
    if current_price and target_price:
        upside = ((target_price - current_price) / current_price) * 100
        upside_text = f"+{upside:.0f}%" if upside >= 0 else f"{upside:.0f}%"

    og_title = f"{ticker}: {recommendation} - {upside_text} Upside" if upside_text else f"{ticker}: {recommendation}"
    og_description = f"AI-powered research report for {company_name}. Target: ₹{target_price:,.0f} | Current: ₹{current_price:,.0f}"
    og_image = f"https://api.permabullish.com/api/reports/{report_cache_id}/og-image"

    # Wrap report in a minimal standalone page with back navigation
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{company_name} ({ticker}) - Permabullish</title>

    <!-- Open Graph / Social Media -->
    <meta property="og:type" content="article">
    <meta property="og:title" content="{og_title}">
    <meta property="og:description" content="{og_description}">
    <meta property="og:image" content="{og_image}">
    <meta property="og:image:width" content="1200">
    <meta property="og:image:height" content="630">
    <meta property="og:site_name" content="Permabullish">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{og_title}">
    <meta name="twitter:description" content="{og_description}">
    <meta name="twitter:image" content="{og_image}">

    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}
        .nav {{
            position: sticky;
            top: 0;
            z-index: 100;
            background: linear-gradient(135deg, #102a43 0%, #1e3a5f 100%);
            color: white;
            padding: 12px 16px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .nav a {{
            color: white;
            text-decoration: none;
            display: flex;
            align-items: center;
            gap: 4px;
        }}
        .nav-title {{
            font-weight: 600;
            font-size: 14px;
        }}
        .btn {{
            background: #e8913a;
            color: white;
            padding: 8px 16px;
            border-radius: 8px;
            text-decoration: none;
            font-size: 14px;
            font-weight: 500;
        }}
        .report-content {{
            padding: 0;
        }}
        .footer {{
            text-align: center;
            padding: 20px;
            background: #f3f4f6;
            font-size: 12px;
            color: #6b7280;
        }}
        .footer a {{
            color: #e8913a;
            text-decoration: none;
        }}
        .cta-section {{
            background: linear-gradient(135deg, #102a43 0%, #1e3a5f 100%);
            padding: 24px 16px;
            text-align: center;
            color: white;
        }}
        .cta-section h3 {{
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 8px;
        }}
        .cta-section p {{
            font-size: 14px;
            color: #9fb3c8;
            margin-bottom: 16px;
        }}
        .cta-buttons {{
            display: flex;
            flex-direction: column;
            gap: 10px;
            max-width: 300px;
            margin: 0 auto;
        }}
        .btn-primary {{
            background: #e8913a;
            color: white;
            padding: 12px 24px;
            border-radius: 8px;
            text-decoration: none;
            font-size: 15px;
            font-weight: 600;
            text-align: center;
        }}
        .btn-secondary {{
            background: rgba(255,255,255,0.1);
            color: white;
            padding: 12px 24px;
            border-radius: 8px;
            text-decoration: none;
            font-size: 15px;
            font-weight: 500;
            text-align: center;
            border: 1px solid rgba(255,255,255,0.2);
        }}
        .bottom-bar {{
            position: sticky;
            bottom: 0;
            background: white;
            border-top: 1px solid #e5e7eb;
            padding: 12px 16px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 -2px 10px rgba(0,0,0,0.1);
        }}
        .bottom-bar a {{
            text-decoration: none;
            font-size: 14px;
        }}
        .bottom-link {{
            color: #6b7280;
        }}
    </style>
</head>
<body>
    <nav class="nav">
        <a href="{FRONTEND_URL}" style="font-weight: 600; font-size: 14px;">Permabullish</a>
        <a href="{FRONTEND_URL}/generate.html" class="btn">Try Free</a>
    </nav>
    <div class="report-content">
        {report_html}
    </div>
    <div class="cta-section">
        <h3>Like this report?</h3>
        <p>Get AI-powered research on 3000+ Indian stocks</p>
        <div class="cta-buttons">
            <a href="{FRONTEND_URL}" class="btn-primary">Sign Up Free</a>
        </div>
    </div>
    <div class="footer">
        <p>AI-powered stock research by <a href="{FRONTEND_URL}">Permabullish</a></p>
        <p style="margin-top: 4px;">Available in English, हिंदी, ગુજરાતી & ಕನ್ನಡ</p>
        <p style="margin-top: 8px;">Not financial advice. For educational purposes only.</p>
    </div>
    <div class="bottom-bar">
        <a href="{FRONTEND_URL}" class="bottom-link">Home</a>
        <a href="{FRONTEND_URL}/generate.html" class="btn" style="padding: 8px 16px; font-size: 13px;">Generate Report</a>
    </div>
</body>
</html>"""

    return HTMLResponse(content=html)


# ============================================
# Share Card Generation
# ============================================

@app.get("/api/reports/{report_cache_id}/og-image")
async def get_report_og_image(report_cache_id: int):
    """Generate and return Open Graph image for social sharing."""
    report = db.get_cached_report_by_id(report_cache_id)

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found"
        )

    # Generate share card image
    image_bytes = share_card.generate_share_card(
        company_name=report.get("company_name", report.get("ticker", "Unknown")),
        ticker=report.get("ticker", ""),
        exchange=report.get("exchange", "NSE"),
        sector=report.get("sector", ""),
        recommendation=report.get("recommendation", "HOLD"),
        current_price=report.get("current_price"),
        target_price=report.get("ai_target_price"),
    )

    return Response(
        content=image_bytes,
        media_type="image/png",
        headers={
            "Cache-Control": "public, max-age=86400",  # Cache for 24 hours
        }
    )


@app.get("/api/reports/{report_cache_id}/share", response_class=HTMLResponse)
async def get_report_share_page(report_cache_id: int):
    """Return HTML page with OG meta tags for social sharing. Redirects to actual report."""
    report = db.get_cached_report_by_id(report_cache_id)

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found"
        )

    # Determine API base URL
    if ENVIRONMENT == "production":
        api_base = "https://api.permabullish.com/api"
    else:
        api_base = "https://permabullish-api.onrender.com/api"

    html = share_card.generate_share_html(
        report_id=report_cache_id,
        company_name=report.get("company_name", report.get("ticker", "Unknown")),
        ticker=report.get("ticker", ""),
        recommendation=report.get("recommendation", "HOLD"),
        current_price=report.get("current_price"),
        target_price=report.get("ai_target_price"),
        api_base=api_base,
        frontend_url=FRONTEND_URL,
    )

    return HTMLResponse(content=html)


# ============================================
# Comparison Share Card Generation
# ============================================

@app.get("/api/comparisons/{comparison_id}/og-image")
async def get_comparison_og_image(comparison_id: int):
    """Generate and return Open Graph image for comparison social sharing."""
    comparison = db.get_comparison_by_id(comparison_id)

    if not comparison:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comparison not found"
        )

    # Generate share card image
    image_bytes = share_card.generate_comparison_share_card(
        ticker_a=comparison.get("ticker_a", ""),
        ticker_b=comparison.get("ticker_b", ""),
        verdict=comparison.get("verdict", "EITHER"),
        verdict_stock=comparison.get("verdict_stock", ""),
        conviction=comparison.get("conviction", "MEDIUM"),
        one_line_verdict=comparison.get("one_line_verdict", ""),
    )

    return Response(
        content=image_bytes,
        media_type="image/png",
        headers={
            "Cache-Control": "public, max-age=86400",  # Cache for 24 hours
        }
    )


@app.get("/api/comparisons/{comparison_id}/share", response_class=HTMLResponse)
async def get_comparison_share_page(comparison_id: int):
    """Return HTML page with OG meta tags for comparison social sharing. Redirects to comparison page."""
    comparison = db.get_comparison_by_id(comparison_id)

    if not comparison:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comparison not found"
        )

    # Determine API base URL
    if ENVIRONMENT == "production":
        api_base = "https://api.permabullish.com/api"
    else:
        api_base = "https://permabullish-api.onrender.com/api"

    html = share_card.generate_comparison_share_html(
        comparison_id=comparison_id,
        ticker_a=comparison.get("ticker_a", ""),
        ticker_b=comparison.get("ticker_b", ""),
        verdict=comparison.get("verdict", "EITHER"),
        verdict_stock=comparison.get("verdict_stock", ""),
        conviction=comparison.get("conviction", "MEDIUM"),
        one_line_verdict=comparison.get("one_line_verdict", ""),
        api_base=api_base,
        frontend_url=FRONTEND_URL,
    )

    return HTMLResponse(content=html)


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


class CheckoutRequest(BaseModel):
    tier: str
    period: int = 1  # 1, 6, or 12 months


@app.post("/api/subscription/checkout")
async def initiate_checkout(
    request_data: CheckoutRequest,
    current_user: dict = Depends(auth.get_current_user)
):
    """
    Initiate subscription checkout via Cashfree.
    Creates a payment order and returns the payment session for frontend SDK.
    """
    tier = request_data.tier
    period = request_data.period

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
            "email": "mail@mayaskara.com"
        }

    # Check for downgrade attempts (not allowed for active subscriptions)
    current_status = db.get_subscription_status(current_user["id"])
    if current_status and not current_status.get("is_expired", True):
        current_tier = current_status.get("tier", "free")

        # Tier hierarchy: free=0, basic=1, pro=2
        tier_rank = {"free": 0, "basic": 1, "pro": 2, "enterprise": 3}
        current_rank = tier_rank.get(current_tier, 0)
        target_rank = tier_rank.get(tier, 0)

        # Block tier downgrade
        if target_rank < current_rank:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Downgrades are not allowed. You currently have {current_status.get('tier_name', current_tier)} plan."
            )

        # Period upgrades are always allowed (1→6, 6→12 months)
        # Only block if buying shorter period than remaining time (period downgrade)
        # Note: Upgrading tier is always allowed regardless of period

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

    if not amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pricing not available for this tier/period"
        )

    # Generate unique order ID
    order_id = cashfree.generate_order_id(current_user["id"], tier, period)

    # Create Cashfree order
    result = cashfree.create_order(
        order_id=order_id,
        amount=amount,
        customer_id=str(current_user["id"]),
        customer_email=current_user["email"],
        customer_name=current_user.get("full_name", current_user["email"]),
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("error", "Failed to create payment order")
        )

    return {
        "type": "checkout",
        "order_id": result["order_id"],
        "payment_session_id": result["payment_session_id"],
        "cf_order_id": result.get("cf_order_id"),
        "tier": tier,
        "tier_name": tier_config.get("name"),
        "period_months": period,
        "amount": amount,
        "currency": "INR",
        "message": "Use payment_session_id with Cashfree JS SDK to complete payment"
    }


@app.get("/api/subscription/verify/{order_id}")
async def verify_payment(
    order_id: str,
    current_user: dict = Depends(auth.get_current_user)
):
    """
    Verify payment status for an order.
    Called by frontend after user returns from payment page.
    """
    # Get order status from Cashfree
    order_result = cashfree.get_order_status(order_id)

    if not order_result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=order_result.get("error", "Failed to verify order")
        )

    order_status = order_result.get("order_status")

    # If order is PAID, get payment details and activate subscription
    if order_status == "PAID":
        payment_result = cashfree.get_payment_details(order_id)

        # Parse order metadata
        order_meta = cashfree.parse_order_id_metadata(order_id)
        user_id = order_meta.get("user_id")
        tier = order_meta.get("tier")
        period = order_meta.get("period_months")

        # Verify the order belongs to this user
        if user_id != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Order does not belong to this user"
            )

        if tier and period and tier in SUBSCRIPTION_TIERS:
            tier_config = SUBSCRIPTION_TIERS[tier]

            # Determine amount
            if period == 1:
                amount = tier_config.get("price_monthly", 0)
            elif period == 6:
                amount = tier_config.get("price_6months", 0)
            elif period == 12:
                amount = tier_config.get("price_yearly", 0)
            else:
                amount = order_result.get("order_amount", 0)

            # Get payment ID from successful payment
            payment_id = None
            if payment_result.get("successful_payment"):
                payment_id = payment_result["successful_payment"].get("cf_payment_id")

            # Create subscription record
            subscription_id = db.create_subscription_record(
                user_id=current_user["id"],
                tier=tier,
                period_months=period,
                amount_paid=amount,
                payment_id=payment_id or order_id
            )

            # Send purchase confirmation email
            try:
                from email_service import send_purchase_email, get_first_name
                from datetime import datetime, timedelta
                expiry_date = (datetime.now() + timedelta(days=period * 30)).strftime("%B %d, %Y")
                first_name = get_first_name(current_user.get("full_name", ""))
                reports_per_month = tier_config.get("reports_limit", 50)
                send_purchase_email(
                    user_email=current_user["email"],
                    first_name=first_name,
                    plan_name=tier_config.get("name", tier.title()),
                    reports_per_month=reports_per_month,
                    expiry_date=expiry_date
                )
            except Exception as e:
                print(f"[PAYMENT] Failed to send purchase email: {e}")

            return {
                "success": True,
                "status": "PAID",
                "message": f"Subscription activated: {tier_config.get('name')}",
                "subscription_id": subscription_id,
                "tier": tier,
                "tier_name": tier_config.get("name"),
                "period_months": period,
                "amount": amount
            }

    # Return current status for non-PAID orders
    return {
        "success": order_status == "PAID",
        "status": order_status,
        "order_id": order_id,
        "amount": order_result.get("order_amount"),
        "message": f"Order status: {order_status}"
    }


@app.post("/api/subscription/activate")
async def activate_subscription(
    tier: str,
    period: int,
    payment_id: str = "mock_payment",
    current_user: dict = Depends(auth.get_current_user)
):
    """
    Manually activate subscription (for testing or manual activation).
    In production, use /verify/{order_id} after Cashfree payment.
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


@app.post("/api/webhooks/cashfree")
async def cashfree_webhook(request: Request):
    """
    Handle Cashfree payment webhook events.
    This is called by Cashfree when payment status changes.
    """
    try:
        # Get raw body for signature verification
        body = await request.body()

        # Get signature headers
        signature = request.headers.get("x-webhook-signature", "")
        timestamp = request.headers.get("x-webhook-timestamp", "")

        # Verify signature (optional but recommended)
        # Note: In sandbox, signature verification might be skipped for testing
        # if not cashfree.verify_webhook_signature(body, signature, timestamp):
        #     raise HTTPException(status_code=401, detail="Invalid signature")

        # Parse webhook payload
        payload = json.loads(body)
        event_type = payload.get("type")
        data = payload.get("data", {})

        # Handle PAYMENT_SUCCESS event
        if event_type == "PAYMENT_SUCCESS_WEBHOOK":
            order_data = data.get("order", {})
            payment_data = data.get("payment", {})

            order_id = order_data.get("order_id")
            payment_status = payment_data.get("payment_status")

            if payment_status == "SUCCESS" and order_id:
                # Parse order metadata
                order_meta = cashfree.parse_order_id_metadata(order_id)
                user_id = order_meta.get("user_id")
                tier = order_meta.get("tier")
                period = order_meta.get("period_months")

                if user_id and tier and period and tier in SUBSCRIPTION_TIERS:
                    tier_config = SUBSCRIPTION_TIERS[tier]

                    # Determine amount
                    if period == 1:
                        amount = tier_config.get("price_monthly", 0)
                    elif period == 6:
                        amount = tier_config.get("price_6months", 0)
                    elif period == 12:
                        amount = tier_config.get("price_yearly", 0)
                    else:
                        amount = order_data.get("order_amount", 0)

                    # Create subscription record
                    payment_id = payment_data.get("cf_payment_id", order_id)
                    db.create_subscription_record(
                        user_id=user_id,
                        tier=tier,
                        period_months=period,
                        amount_paid=amount,
                        payment_id=payment_id
                    )

                    print(f"[WEBHOOK] Subscription activated for user {user_id}: {tier} ({period}m)")

                    # Send purchase confirmation email
                    try:
                        user = db.get_user_by_id(user_id)
                        if user:
                            from email_service import send_purchase_email, get_first_name
                            from datetime import datetime, timedelta
                            expiry_date = (datetime.now() + timedelta(days=period * 30)).strftime("%B %d, %Y")
                            first_name = get_first_name(user.get("full_name", ""))
                            reports_per_month = tier_config.get("reports_limit", 50)
                            send_purchase_email(
                                user_email=user["email"],
                                first_name=first_name,
                                plan_name=tier_config.get("name", tier.title()),
                                reports_per_month=reports_per_month,
                                expiry_date=expiry_date
                            )
                    except Exception as e:
                        print(f"[WEBHOOK] Failed to send purchase email: {e}")

        return {"status": "received", "event_type": event_type}

    except Exception as e:
        print(f"[WEBHOOK ERROR] {str(e)}")
        return {"status": "error", "message": str(e)}


@app.post("/api/webhooks/payment-form")
async def payment_form_webhook(request: Request):
    """
    Handle Cashfree Payment Form webhook events.
    This is called when a customer pays via a payment form.
    Matches customer email to user account and activates subscription.
    """
    try:
        body = await request.body()
        payload = json.loads(body)

        event_type = payload.get("type")
        data = payload.get("data", {})

        print(f"[PAYMENT FORM WEBHOOK] Event: {event_type}")
        print(f"[PAYMENT FORM WEBHOOK] Data: {json.dumps(data, indent=2)}")

        # Handle payment form webhook - check for multiple event type formats
        # Cashfree may send "PAYMENT_SUCCESS_WEBHOOK", "success payment", or "payment_form_order_webhook"
        is_success_event = (
            event_type in ["payment_form_order_webhook", "PAYMENT_SUCCESS_WEBHOOK"] or
            (event_type and "success" in event_type.lower())
        )

        if is_success_event:
            # Try different payload structures
            order = data.get("order", {})
            customer = data.get("customer_details", {}) or data.get("customer", {})
            payment = data.get("payment", {})
            form = data.get("form", {})

            # Get order status from various possible locations
            order_status = (
                order.get("order_status") or
                payment.get("payment_status") or
                data.get("payment_status") or
                "PAID"  # Assume paid if this is a success event
            )

            # Get customer email from various possible locations
            customer_email = (
                customer.get("customer_email") or
                customer.get("email") or
                data.get("customer_email") or
                ""
            ).lower().strip()

            # Get amount from various possible locations
            amount = float(
                order.get("order_amount") or
                payment.get("payment_amount") or
                data.get("order_amount") or
                0
            )

            # Get payment ID
            payment_id = (
                order.get("cf_order_id") or
                order.get("order_id") or
                payment.get("cf_payment_id") or
                data.get("cf_order_id") or
                "unknown"
            )

            print(f"[PAYMENT FORM WEBHOOK] Parsed: email={customer_email}, amount={amount}, status={order_status}")

            if customer_email:
                # Look up user by email
                user = db.get_user_by_email(customer_email)

                if not user:
                    print(f"[PAYMENT FORM WEBHOOK] User not found for email: {customer_email}")
                    # Store payment for manual reconciliation
                    return {
                        "status": "user_not_found",
                        "email": customer_email,
                        "amount": amount,
                        "message": "Payment received but user not found. Manual activation required."
                    }

                # Determine tier and period from amount
                # This mapping should match your payment form prices
                tier, period = None, None

                # Basic plans
                if amount == 999:
                    tier, period = "basic", 1
                elif amount == 3999:
                    tier, period = "basic", 6
                elif amount == 7499:
                    tier, period = "basic", 12
                # Pro plans
                elif amount == 1499:
                    tier, period = "pro", 1
                elif amount == 5999:
                    tier, period = "pro", 6
                elif amount == 9999:
                    tier, period = "pro", 12
                else:
                    # Test mode: any other amount gives 1 month basic
                    print(f"[PAYMENT FORM WEBHOOK] Test mode - unknown amount {amount}, granting 1 month basic")
                    tier, period = "basic", 1

                # Create subscription
                tier_config = SUBSCRIPTION_TIERS.get(tier, {})
                subscription_id = db.create_subscription_record(
                    user_id=user["id"],
                    tier=tier,
                    period_months=period,
                    amount_paid=amount,
                    payment_id=f"pf_{payment_id}"
                )

                print(f"[PAYMENT FORM WEBHOOK] Subscription activated for {customer_email}: {tier} ({period}m)")

                # Send purchase confirmation email
                try:
                    from email_service import send_purchase_email, get_first_name
                    from datetime import datetime, timedelta
                    expiry_date = (datetime.now() + timedelta(days=period * 30)).strftime("%B %d, %Y")
                    first_name = get_first_name(user.get("full_name", ""))
                    reports_per_month = tier_config.get("reports_limit", 50)
                    send_purchase_email(
                        user_email=customer_email,
                        first_name=first_name,
                        plan_name=tier_config.get("name", tier.title()),
                        reports_per_month=reports_per_month,
                        expiry_date=expiry_date
                    )
                except Exception as e:
                    print(f"[PAYMENT FORM WEBHOOK] Failed to send purchase email: {e}")

                return {
                    "status": "success",
                    "email": customer_email,
                    "user_id": user["id"],
                    "subscription_id": subscription_id,
                    "tier": tier,
                    "period_months": period,
                    "message": f"Subscription activated: {tier_config.get('name', tier)}"
                }

        return {"status": "received", "event_type": event_type}

    except Exception as e:
        print(f"[PAYMENT FORM WEBHOOK ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e)}


@app.get("/api/admin/test-cashfree")
async def test_cashfree_connection(secret: str = ""):
    """Test Cashfree API connection. Requires admin secret."""
    admin_secret = os.getenv("ADMIN_SECRET", "permabullish-test-2024")
    if secret != admin_secret:
        raise HTTPException(status_code=403, detail="Invalid admin secret")

    result = cashfree.test_connection()
    return result


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
