"""Authentication middleware for FastAPI."""

from typing import Optional

from fastapi import Depends, HTTPException, Header, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.local import LocalAuthService
from app.auth.models import AuthProvider, User, UserAccount
from app.logging_config import get_logger

logger = get_logger(__name__)

# Security scheme
security = HTTPBearer(auto_error=False)

# Auth service instance
auth_service = LocalAuthService()


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    x_client_type: str = Header(default="public", alias="X-Client-Type"),
) -> UserAccount | None:
    """Get current authenticated user.

    Supports both:
    - Local JWT tokens (public frontend)
    - Zitadel tokens (internal/SalesAI frontend)

    Args:
        request: FastAPI request
        credentials: Bearer token
        x_client_type: Client type header (public/internal)

    Returns:
        User account or None if not authenticated
    """
    if not credentials:
        return None

    token = credentials.credentials

    # Determine auth method based on client type
    if x_client_type == "internal":
        # Zitadel OIDC token - validate with Zitadel
        user = await _validate_zitadel_token(token)
    else:
        # Local JWT token
        user = auth_service.get_user_from_token(token)

    if user:
        # Store user in request state for later use
        request.state.user = user
        request.state.client_type = x_client_type

    return user


async def _validate_zitadel_token(token: str) -> UserAccount | None:
    """Validate Zitadel OIDC token.

    In production, this would:
    1. Validate token with Zitadel introspection endpoint
    2. Get user info from Zitadel
    3. Create/update local user record

    Args:
        token: Zitadel access token

    Returns:
        User account or None
    """
    # TODO: Implement Zitadel validation
    # For now, this is a placeholder

    # In production:
    # 1. Call Zitadel introspection endpoint
    # 2. Get user info
    # 3. Find or create local user with external_id

    from app.settings import settings

    zitadel_url = getattr(settings, "zitadel_url", None)
    if not zitadel_url:
        logger.warning("zitadel_not_configured")
        return None

    # Placeholder - implement actual Zitadel validation
    logger.debug("zitadel_validation_not_implemented")
    return None


def require_auth(user: UserAccount | None = Depends(get_current_user)) -> UserAccount:
    """Require authentication - raises 401 if not authenticated.

    Args:
        user: Current user from get_current_user

    Returns:
        Authenticated user

    Raises:
        HTTPException: 401 if not authenticated
    """
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_admin(user: UserAccount = Depends(require_auth)) -> UserAccount:
    """Require admin privileges.

    Args:
        user: Authenticated user

    Returns:
        Admin user

    Raises:
        HTTPException: 403 if not admin
    """
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


def require_subscription(
    tier: str = "pro",
    user: UserAccount = Depends(require_auth),
) -> UserAccount:
    """Require specific subscription tier.

    Args:
        tier: Required tier (free, pro, enterprise)
        user: Authenticated user

    Returns:
        User with required subscription

    Raises:
        HTTPException: 403 if insufficient subscription
    """
    from app.auth.models import SubscriptionTier

    tier_order = {
        SubscriptionTier.FREE: 0,
        SubscriptionTier.PRO: 1,
        SubscriptionTier.ENTERPRISE: 2,
    }

    required_level = tier_order.get(SubscriptionTier(tier), 0)
    user_level = tier_order.get(user.subscription_tier, 0)

    if user_level < required_level:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Subscription tier '{tier}' required",
        )

    return user


def require_credits(
    amount: float,
    user: UserAccount = Depends(require_auth),
) -> UserAccount:
    """Require sufficient credits.

    Args:
        amount: Required credit amount
        user: Authenticated user

    Returns:
        User with sufficient credits

    Raises:
        HTTPException: 402 if insufficient credits
    """
    if user.credits_balance < amount:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Insufficient credits. Required: {amount}, Available: {user.credits_balance}",
        )

    return user


class ClientTypeChecker:
    """Dependency to check client type and restrict access."""

    def __init__(self, allowed_types: list[str]):
        """Initialize checker.

        Args:
            allowed_types: List of allowed client types
        """
        self.allowed_types = allowed_types

    def __call__(
        self,
        request: Request,
        x_client_type: str = Header(default="public", alias="X-Client-Type"),
    ):
        """Check client type.

        Args:
            request: FastAPI request
            x_client_type: Client type header

        Raises:
            HTTPException: 403 if client type not allowed
        """
        if x_client_type not in self.allowed_types:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This endpoint is not available for '{x_client_type}' clients",
            )

        return x_client_type


# Pre-configured checkers
require_internal_client = ClientTypeChecker(["internal"])
require_public_client = ClientTypeChecker(["public"])
