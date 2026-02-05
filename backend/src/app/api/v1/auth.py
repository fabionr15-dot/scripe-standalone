"""Authentication API v1 endpoints."""

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field

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


# ==================== MODELS ====================


class RegisterRequest(BaseModel):
    """User registration request."""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    name: str | None = Field(default=None, max_length=100)


class LoginRequest(BaseModel):
    """User login request."""
    email: EmailStr
    password: str


class ChangePasswordRequest(BaseModel):
    """Change password request."""
    old_password: str
    new_password: str = Field(..., min_length=8, max_length=100)


class ResetPasswordRequest(BaseModel):
    """Password reset request."""
    email: EmailStr


class ResetPasswordConfirm(BaseModel):
    """Password reset confirmation."""
    token: str
    new_password: str = Field(..., min_length=8, max_length=100)


class UpdateProfileRequest(BaseModel):
    """Update profile request."""
    name: str | None = None
    default_country: str | None = Field(default=None, min_length=2, max_length=2)
    default_language: str | None = Field(default=None, min_length=2, max_length=5)


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


# ==================== ENDPOINTS ====================


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register(request: Request, body: RegisterRequest):
    """Register a new user account.

    Creates a local (email/password) account with welcome credits.
    """
    try:
        # Create user
        user = auth_service.create_user(
            email=body.email,
            password=body.password,
            name=body.name,
        )

        # Create access token
        token = auth_service.create_access_token(user)

        logger.info("user_registered", user_id=user.id, email=body.email)

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
    user = auth_service.authenticate(body.email, body.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

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

    Note: Always returns success to prevent email enumeration.
    """
    token = auth_service.generate_reset_token(body.email)

    if token:
        # TODO: Send email with reset link
        # In production: send_reset_email(body.email, token)
        logger.info("password_reset_requested", email=body.email)

    # Always return success to prevent email enumeration
    return {
        "success": True,
        "message": "If an account exists with this email, a reset link has been sent",
    }


@router.post("/reset-password")
async def reset_password(request: ResetPasswordConfirm):
    """Reset password with token."""
    success = auth_service.reset_password(request.token, request.new_password)

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
async def resend_verification(user: UserAccount = Depends(require_auth)):
    """Resend email verification."""
    if user.email_verified:
        return {"success": True, "message": "Email already verified"}

    token = auth_service.generate_verification_token(user.id)

    # TODO: Send verification email
    # In production: send_verification_email(user.email, token)

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
            # Fallback: test mode (development only)
            if _settings.env == "development":
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
            raise ValueError("Pagamenti non configurati")

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
                user = UserAccount(
                    email=test_email,
                    name="Test User",
                    auth_provider=AuthProvider.LOCAL,
                    password_hash="test_mode_no_password",
                    subscription_tier=SubscriptionTier.PRO,
                    credits_balance=1000.0,
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
