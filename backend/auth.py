"""
Authentication module with subscription tier support.
Payment integration via Cashfree (Phase 3).
"""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, SUBSCRIPTION_TIERS
import database as db

# Password hashing - using pbkdf2_sha256 (no length limit, secure)
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

# Bearer token security
security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)


def _prepare_password(password: str) -> str:
    """Prepare password for hashing (handle any preprocessing)."""
    return password


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(_prepare_password(plain_password), hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(_prepare_password(password))


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def create_verification_token(user_id: int, email: str) -> str:
    """Create a JWT token for email verification (24-hour expiry)."""
    return jwt.encode(
        {
            "sub": str(user_id),
            "email": email,
            "purpose": "email_verify",
            "exp": datetime.utcnow() + timedelta(hours=24),
        },
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


def create_password_reset_token(user_id: int, email: str) -> str:
    """Create a JWT token for password reset (1-hour expiry)."""
    return jwt.encode(
        {
            "sub": str(user_id),
            "email": email,
            "purpose": "password_reset",
            "exp": datetime.utcnow() + timedelta(hours=1),
        },
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


def decode_purpose_token(token: str, expected_purpose: str) -> Optional[dict]:
    """Decode and validate a purpose-specific token (verification or reset)."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("purpose") != expected_purpose:
            return None
        return payload
    except JWTError:
        return None


def get_user_subscription_tier(user: dict) -> str:
    """Get user's subscription tier, defaulting to 'free'."""
    return user.get("subscription_tier", "free")


def get_tier_features(tier: str) -> dict:
    """Get features for a subscription tier."""
    return SUBSCRIPTION_TIERS.get(tier, SUBSCRIPTION_TIERS["free"])["features"]


def get_tier_report_limit(tier: str) -> int:
    """Get monthly report limit for a subscription tier."""
    return SUBSCRIPTION_TIERS.get(tier, SUBSCRIPTION_TIERS["free"])["monthly_reports"]


def can_access_feature(user: dict, feature: str) -> bool:
    """Check if user can access a specific feature based on their subscription."""
    tier = get_user_subscription_tier(user)
    features = get_tier_features(tier)
    return features.get(feature, False)


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Dependency to get current authenticated user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = credentials.credentials
    payload = decode_token(token)

    if payload is None:
        raise credentials_exception

    user_id: int = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    user = db.get_user_by_id(int(user_id))
    if user is None:
        raise credentials_exception

    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )

    return user


async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security)
) -> Optional[dict]:
    """
    Dependency to get current user if authenticated, None otherwise.
    Use this for routes that work for both authenticated and anonymous users.
    """
    if credentials is None:
        return None

    token = credentials.credentials
    payload = decode_token(token)

    if payload is None:
        return None

    user_id = payload.get("sub")
    if user_id is None:
        return None

    user = db.get_user_by_id(int(user_id))
    if user is None:
        return None

    if not user.get("is_active", True):
        return None

    return user


def require_feature(feature: str):
    """
    Dependency factory to require a specific feature access.
    Usage: Depends(require_feature("mf_analytics"))
    """
    async def _require_feature(current_user: dict = Depends(get_current_user)) -> dict:
        if not can_access_feature(current_user, feature):
            tier = get_user_subscription_tier(current_user)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This feature requires a higher subscription tier. Current: {tier}"
            )
        return current_user
    return _require_feature


def register_user(email: str, password: str, full_name: str) -> tuple[bool, str, Optional[dict]]:
    """
    Register a new user.
    Returns: (success, message, user_data)
    """
    # Normalize email to lowercase
    email = email.lower().strip()

    # Validate email format
    if "@" not in email or "." not in email:
        return False, "Invalid email format", None

    # Validate password strength
    if len(password) < 8:
        return False, "Password must be at least 8 characters", None

    # Check if user already exists
    existing_user = db.get_user_by_email(email)
    if existing_user:
        if existing_user.get("auth_provider") == "google" and existing_user.get("password_hash") is None:
            return False, "Email already registered. Try signing in with Google.", None
        return False, "Email already registered", None

    # Create user
    password_hash = get_password_hash(password)
    user_id = db.create_user(email, password_hash, full_name)

    if user_id is None:
        return False, "Failed to create user", None

    # Don't send welcome email here - send verification email instead (handled by endpoint)
    return True, "User created successfully", {
        "id": user_id,
        "email": email,
        "full_name": full_name,
        "subscription_tier": "free"
    }


def authenticate_user(email: str, password: str) -> tuple[bool, str, Optional[str]]:
    """
    Authenticate user and return token.
    Returns: (success, message, token)
    """
    email = email.lower().strip()
    user = db.get_user_by_email(email)

    if not user:
        return False, "Invalid email or password", None

    # Check if user is Google-only (no password)
    if user.get("password_hash") is None:
        return False, "Please sign in with Google", None

    if not verify_password(password, user["password_hash"]):
        return False, "Invalid email or password", None

    if not user.get("is_active", True):
        return False, "Account is disabled", None

    # Check if email is verified (only for email/password users)
    if not user.get("email_verified", False):
        return False, "Please verify your email before signing in. Check your inbox for the verification link.", None

    # Create access token
    access_token = create_access_token(
        data={"sub": str(user["id"]), "email": user["email"]}
    )

    return True, "Login successful", access_token
