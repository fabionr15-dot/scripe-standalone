"""Authentication API v1 endpoints."""

import re
import time
from collections import defaultdict
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field, field_validator

from app.api.rate_limit import limiter
from app.auth.credits import CreditService
from app.auth.local import LocalAuthService, JWT_EXPIRE_HOURS
from app.auth.middleware import get_current_user, require_auth
from app.auth.models import (
    AuthProvider,
    SubscriptionTier,
    TokenResponse,
    User,
    UserAccount,
    UserCreate,
    UserLogin,
)
from app.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

# Services
auth_service = LocalAuthService()
credit_service = CreditService()

# ==================== ACCOUNT LOCKOUT ====================

# Track failed login attempts: key = email or IP, value = list of timestamps
_failed_attempts: dict[str, list[float]] = defaultdict(list)
_LOCKOUT_THRESHOLD = 5       # Max failed attempts before lockout
_LOCKOUT_WINDOW = 900        # 15 minutes window for counting attempts
_LOCKOUT_DURATION = 900      # 15 minutes lockout duration


def _check_lockout(key: str) -> None:
    """Check if an account/IP is locked out. Raises 429 if locked."""
    now = time.time()
    # Clean up old attempts outside the window
    _failed_attempts[key] = [
        t for t in _failed_attempts[key] if now - t < _LOCKOUT_WINDOW
    ]
    if len(_failed_attempts[key]) >= _LOCKOUT_THRESHOLD:
        oldest_in_window = _failed_attempts[key][0]
        remaining = int(_LOCKOUT_DURATION - (now - oldest_in_window))
        if remaining > 0:
            logger.warning("account_locked_out", key=key, remaining_seconds=remaining)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many failed login attempts. Try again in {remaining // 60 + 1} minutes.",
            )
        # Lockout expired, clear attempts
        _failed_attempts[key].clear()


def _record_failed_attempt(key: str) -> None:
    """Record a failed login attempt."""
    _failed_attempts[key].append(time.time())


# ==================== MODELS ====================


def validate_password_complexity(password: str) -> str:
    """Validate password meets security requirements."""
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters")
    if len(password) > 100:
        raise ValueError("Password must be at most 100 characters")
    if not re.search(r'[A-Z]', password):
        raise ValueError("Password must contain at least one uppercase letter")
    if not re.search(r'[a-z]', password):
        raise ValueError("Password must contain at least one lowercase letter")
    if not re.search(r'[0-9]', password):
        raise ValueError("Password must contain at least one digit")
    if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\;\'`~]', password):
        raise ValueError("Password must contain at least one special character")
    return password


class RegisterRequest(BaseModel):
    """User registration request."""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    name: str | None = Field(default=None, max_length=100)
    referral_code: str | None = Field(default=None, max_length=20)  # Optional referral code

    @field_validator('password')
    @classmethod
    def check_password_complexity(cls, v):
        return validate_password_complexity(v)


class LoginRequest(BaseModel):
    """User login request."""
    email: EmailStr
    password: str


class ChangePasswordRequest(BaseModel):
    """Change password request."""
    old_password: str
    new_password: str = Field(..., min_length=8, max_length=100)

    @field_validator('new_password')
    @classmethod
    def check_password_complexity(cls, v):
        return validate_password_complexity(v)


class ResetPasswordRequest(BaseModel):
    """Password reset request."""
    email: EmailStr


class ResetPasswordConfirm(BaseModel):
    """Password reset confirmation."""
    token: str
    new_password: str = Field(..., min_length=8, max_length=100)

    @field_validator('new_password')
    @classmethod
    def check_password_complexity(cls, v):
        return validate_password_complexity(v)


class UpdateProfileRequest(BaseModel):
    """Update profile request."""
    name: str | None = None
    default_country: str | None = Field(default=None, min_length=2, max_length=2)
    default_language: str | None = Field(default=None, min_length=2, max_length=5)
    # Company / Billing fields
    company_name: str | None = Field(default=None, max_length=255)
    vat_id: str | None = Field(default=None, max_length=50)  # USt-IdNr.
    billing_email: str | None = Field(default=None, max_length=255)


class UserResponse(BaseModel):
    """User response."""
    id: int
    email: str
    name: str | None
    auth_provider: str
    subscription_tier: str
    credits_balance: float
    email_verified: bool
    is_active: bool
    default_country: str
    default_language: str
    # Company / Billing fields
    company_name: str | None = None
    vat_id: str | None = None
    billing_email: str | None = None
    tax_exempt: bool = False


# ==================== ENDPOINTS ====================


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register(request: Request, body: RegisterRequest):
    """Register a new user account.

    Creates a local (email/password) account with welcome credits.
    If referral_code is provided, gives bonus credits to both users.
    Sends verification and welcome emails.
    """
    from app.email.service import email_service
    from app.referral.service import referral_service

    try:
        # Validate referral code if provided
        referrer_id = None
        referral_code_obj = None
        if body.referral_code:
            referral_code_obj = referral_service.validate_code(body.referral_code)
            if referral_code_obj:
                referrer_id = referral_code_obj.user_id
                logger.info(
                    "registration_with_referral",
                    referral_code=body.referral_code,
                    referrer_id=referrer_id,
                )

        # Create user with extra credits if referred (20 instead of 10)
        extra_credits = 10.0 if referrer_id else 0.0  # Referral bonus
        user = auth_service.create_user(
            email=body.email,
            password=body.password,
            name=body.name,
            extra_credits=extra_credits,
        )

        # Process referral if applicable
        if referrer_id and referral_code_obj:
            referral_service.process_signup(
                referrer_id=referrer_id,
                referred_id=user.id,
                referral_code_id=referral_code_obj.id,
            )

        # Create access token
        token = auth_service.create_access_token(user)

        logger.info(
            "user_registered",
            user_id=user.id,
            email=body.email,
            referred_by=referrer_id,
        )

        # Send verification email
        verification_token = auth_service.generate_verification_token(user.id)
        await email_service.send_verification_email(
            to_email=user.email,
            user_name=user.name,
            verification_token=verification_token,
        )

        # Send welcome email (mentions referral bonus if applicable)
        await email_service.send_welcome_email(
            to_email=user.email,
            user_name=user.name,
        )

        return TokenResponse(
            access_token=token,
            token_type="bearer",
            expires_in=JWT_EXPIRE_HOURS * 3600,
            user=User(
                id=user.id,
                email=user.email,
                name=user.name,
                auth_provider=user.auth_provider,
                subscription_tier=user.subscription_tier,
                credits_balance=user.credits_balance,
                is_active=user.is_active,
                created_at=user.created_at,
            ),
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(request: Request, body: LoginRequest):
    """Login with email and password.

    Returns JWT access token for authentication.
    """
    # Check lockout for both email and IP
    email_key = f"email:{body.email.lower()}"
    ip_key = f"ip:{request.client.host if request.client else 'unknown'}"
    _check_lockout(email_key)
    _check_lockout(ip_key)

    user = auth_service.authenticate(body.email, body.password)

    if not user:
        # Record failed attempt for both email and IP
        _record_failed_attempt(email_key)
        _record_failed_attempt(ip_key)
        logger.warning(
            "login_failed",
            email=body.email,
            ip=request.client.host if request.client else "unknown",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Successful login clears failed attempts
    _failed_attempts.pop(email_key, None)
    _failed_attempts.pop(ip_key, None)

    # Create access token
    token = auth_service.create_access_token(user)

    logger.info("user_logged_in", user_id=user.id)

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=JWT_EXPIRE_HOURS * 3600,
        user=User(
            id=user.id,
            email=user.email,
            name=user.name,
            auth_provider=user.auth_provider,
            subscription_tier=user.subscription_tier,
            credits_balance=user.credits_balance,
            is_active=user.is_active,
            created_at=user.created_at,
        ),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(user: UserAccount = Depends(require_auth)):
    """Refresh access token.

    Returns new JWT access token.
    """
    # Get fresh user data
    fresh_user = auth_service.get_user_by_id(user.id)
    if not fresh_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    # Create new token
    token = auth_service.create_access_token(fresh_user)

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=JWT_EXPIRE_HOURS * 3600,
        user=User(
            id=fresh_user.id,
            email=fresh_user.email,
            name=fresh_user.name,
            auth_provider=fresh_user.auth_provider,
            subscription_tier=fresh_user.subscription_tier,
            credits_balance=fresh_user.credits_balance,
            is_active=fresh_user.is_active,
            created_at=fresh_user.created_at,
        ),
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(user: UserAccount = Depends(require_auth)):
    """Get current user information."""
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        auth_provider=user.auth_provider.value,
        subscription_tier=user.subscription_tier.value,
        credits_balance=user.credits_balance,
        email_verified=user.email_verified,
        is_active=user.is_active,
        default_country=user.default_country,
        default_language=user.default_language,
        # Company / Billing fields
        company_name=user.company_name,
        vat_id=user.vat_id,
        billing_email=user.billing_email,
        tax_exempt=user.tax_exempt,
    )


@router.patch("/me", response_model=UserResponse)
async def update_profile(
    request: UpdateProfileRequest,
    user: UserAccount = Depends(require_auth),
):
    """Update user profile."""
    from app.storage.db import db

    with db.session() as session:
        db_user = session.query(UserAccount).filter(
            UserAccount.id == user.id
        ).first()

        if request.name is not None:
            db_user.name = request.name
        if request.default_country is not None:
            db_user.default_country = request.default_country.upper()
        if request.default_language is not None:
            db_user.default_language = request.default_language
        # Company / Billing fields
        if request.company_name is not None:
            db_user.company_name = request.company_name
        if request.vat_id is not None:
            db_user.vat_id = request.vat_id
            # Wenn VAT-ID gesetzt ist, tax_exempt aktivieren (EU Reverse Charge)
            db_user.tax_exempt = bool(request.vat_id.strip())
        if request.billing_email is not None:
            db_user.billing_email = request.billing_email

        session.commit()
        session.refresh(db_user)

        return UserResponse(
            id=db_user.id,
            email=db_user.email,
            name=db_user.name,
            auth_provider=db_user.auth_provider.value,
            subscription_tier=db_user.subscription_tier.value,
            credits_balance=db_user.credits_balance,
            email_verified=db_user.email_verified,
            is_active=db_user.is_active,
            default_country=db_user.default_country,
            default_language=db_user.default_language,
            # Company / Billing fields
            company_name=db_user.company_name,
            vat_id=db_user.vat_id,
            billing_email=db_user.billing_email,
            tax_exempt=db_user.tax_exempt,
        )


@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    user: UserAccount = Depends(require_auth),
):
    """Change user password."""
    if user.auth_provider != AuthProvider.LOCAL:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password change not available for this auth provider",
        )

    success = auth_service.change_password(
        user_id=user.id,
        old_password=request.old_password,
        new_password=request.new_password,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid current password",
        )

    return {"success": True, "message": "Password changed successfully"}


@router.post("/forgot-password")
@limiter.limit("3/minute")
async def forgot_password(request: Request, body: ResetPasswordRequest):
    """Request password reset email.

    Always returns success to prevent email enumeration.
    """
    from app.email.service import email_service

    token = auth_service.generate_reset_token(body.email)
    if token:
        # Get user name for email personalization
        user = auth_service.get_user_by_email(body.email)
        user_name = user.name if user else None

        # Send password reset email
        await email_service.send_password_reset_email(
            to_email=body.email,
            user_name=user_name,
            reset_token=token,
        )
        logger.info("password_reset_requested", email=body.email)

    # Always return success to prevent email enumeration
    return {
        "success": True,
        "message": "If an account exists with this email, a reset link has been sent",
    }


@router.post("/reset-password")
async def reset_password(body: ResetPasswordConfirm):
    """Reset password with token."""
    # Validate new password complexity
    try:
        validate_password_complexity(body.new_password)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    success = auth_service.reset_password(body.token, body.new_password)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )
    return {"success": True, "message": "Password reset successfully"}


@router.post("/verify-email")
async def verify_email(token: str):
    """Verify email with token."""
    success = auth_service.verify_email(token)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token",
        )

    return {"success": True, "message": "Email verified successfully"}


@router.post("/resend-verification")
@limiter.limit("3/minute")
async def resend_verification(request: Request, user: UserAccount = Depends(require_auth)):
    """Resend email verification."""
    from app.email.service import email_service

    if user.email_verified:
        return {"success": True, "message": "Email already verified"}

    token = auth_service.generate_verification_token(user.id)

    # Send verification email
    await email_service.send_verification_email(
        to_email=user.email,
        user_name=user.name,
        verification_token=token,
    )

    return {"success": True, "message": "Verification email sent"}


# ==================== CREDITS ====================


@router.get("/credits")
async def get_credits(user: UserAccount = Depends(require_auth)):
    """Get user's credit balance and usage summary."""
    summary = credit_service.get_usage_summary(user.id)
    return summary


@router.get("/credits/packages")
async def get_credit_packages():
    """Get available credit packages for purchase."""
    return {
        "packages": CreditService.get_packages(),
    }


@router.get("/credits/history")
async def get_credit_history(
    limit: int = 50,
    offset: int = 0,
    user: UserAccount = Depends(require_auth),
):
    """Get credit transaction history."""
    transactions = credit_service.get_transaction_history(
        user_id=user.id,
        limit=limit,
        offset=offset,
    )

    return {
        "transactions": [
            {
                "id": t.id,
                "amount": t.amount,
                "balance_after": t.balance_after,
                "operation": t.operation,
                "description": t.description,
                "search_id": t.search_id,
                "created_at": t.created_at.isoformat(),
            }
            for t in transactions
        ],
    }


class PurchaseRequest(BaseModel):
    """Credit purchase request."""
    package_id: str


@router.post("/credits/purchase")
@limiter.limit("10/minute")
async def purchase_credits(
    request: Request,
    body: PurchaseRequest,
    user: UserAccount = Depends(require_auth),
):
    """Purchase credit package via Stripe Checkout."""
    from app.settings import settings as _settings

    try:
        if not _settings.stripe_secret_key:
            # Fallback: test mode (development only, localhost only)
            client_ip = request.client.host if request.client else ""
            is_localhost = client_ip in ("127.0.0.1", "::1", "localhost")
            if _settings.env == "development" and is_localhost:
                transaction = credit_service.purchase_credits(
                    user_id=user.id,
                    package_id=body.package_id,
                    payment_reference="test_mode",
                )
                return {
                    "success": True,
                    "transaction_id": transaction.id,
                    "credits_added": transaction.amount,
                    "new_balance": transaction.balance_after,
                }
            raise ValueError("Payment system not configured")

        from app.payments.stripe_service import create_checkout_session

        base_url = _settings.allowed_origins.split(",")[0]
        checkout_url = create_checkout_session(
            user_id=user.id,
            user_email=user.email,
            package_id=body.package_id,
            success_url=f"{base_url}/payment/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{base_url}/payment/cancel",
        )

        return {"checkout_url": checkout_url}

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


# ==================== TEST MODE (ONLY IN DEVELOPMENT) ====================

from app.settings import settings as app_settings

if app_settings.env == "development":

    @router.post("/test-login", response_model=TokenResponse)
    async def test_login():
        """DEV ONLY: Auto-login without password.

        Creates or retrieves a test user and returns a valid token.
        Only available when ENV=development.
        """
        from app.storage.db import db
        from datetime import datetime

        test_email = "test@scripe.local"

        with db.session() as session:
            user = session.query(UserAccount).filter(
                UserAccount.email == test_email
            ).first()

            if not user:
                # SECURITY: Test user gets FREE tier with 0 credits
                # This prevents abuse even if endpoint is accidentally exposed
                user = UserAccount(
                    email=test_email,
                    name="Test User (Dev Only)",
                    auth_provider=AuthProvider.LOCAL,
                    password_hash="test_mode_no_password",
                    subscription_tier=SubscriptionTier.FREE,  # FREE, not PRO!
                    credits_balance=0.0,  # No free credits
                    email_verified=True,
                )
                session.add(user)
                session.commit()
                session.refresh(user)
                logger.warning("test_user_created", email=test_email)

            user_id = user.id
            user_email = user.email
            user_name = user.name
            user_auth_provider = user.auth_provider
            user_subscription_tier = user.subscription_tier
            user_credits_balance = user.credits_balance
            user_is_active = user.is_active
            user_created_at = user.created_at or datetime.utcnow()

        class SimpleUser:
            def __init__(self):
                self.id = user_id
                self.email = user_email
                self.auth_provider = user_auth_provider
                self.subscription_tier = user_subscription_tier

        simple_user = SimpleUser()
        token = auth_service.create_access_token(simple_user)

        logger.warning("test_login_used", user_id=user_id)

        return TokenResponse(
            access_token=token,
            token_type="bearer",
            expires_in=JWT_EXPIRE_HOURS * 3600,
            user=User(
                id=user_id,
                email=user_email,
                name=user_name,
                auth_provider=user_auth_provider,
                subscription_tier=user_subscription_tier,
                credits_balance=user_credits_balance,
                is_active=user_is_active,
                created_at=user_created_at,
            ),
        )
