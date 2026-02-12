"""API Key management endpoints.

Allows Pro/Enterprise users to generate API keys for programmatic access.
"""

import secrets
import hashlib
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, Field

from app.auth.middleware import require_auth, get_current_user
from app.auth.models import UserAccount, SubscriptionTier
from app.logging_config import get_logger
from app.storage.db import db

router = APIRouter(prefix="/api-keys", tags=["api-keys"])
logger = get_logger(__name__)


# ─── Models ──────────────────────────────────────────────────────────────────

class CreateAPIKeyRequest(BaseModel):
    """Request to create a new API key."""
    name: str = Field(..., min_length=1, max_length=100)
    scopes: list[str] = Field(default=["read", "search"])


class APIKeyResponse(BaseModel):
    """API key information (without the actual key)."""
    id: int
    name: str
    prefix: str  # First 8 chars of the key
    scopes: list[str]
    created_at: str
    last_used_at: str | None
    is_active: bool


class APIKeyCreatedResponse(BaseModel):
    """Response when a new API key is created.

    IMPORTANT: The full key is only shown once at creation time!
    """
    id: int
    name: str
    key: str  # Full API key - only shown once!
    prefix: str
    scopes: list[str]
    message: str = "Store this key securely. It will not be shown again."


# ─── API Key Storage (using existing models) ─────────────────────────────────

# Note: In a full implementation, we'd have an APIKey model.
# For now, we'll store in user settings_json as a simple implementation.

def _hash_key(key: str) -> str:
    """Hash an API key for secure storage."""
    return hashlib.sha256(key.encode()).hexdigest()


def _generate_api_key() -> str:
    """Generate a new API key."""
    return f"scripe_{secrets.token_urlsafe(32)}"


def _get_user_api_keys(user: UserAccount) -> list[dict]:
    """Get user's API keys from settings."""
    settings = user.settings or {}
    return settings.get("api_keys", [])


def _save_user_api_keys(session, user: UserAccount, keys: list[dict]):
    """Save user's API keys to settings."""
    settings = user.settings or {}
    settings["api_keys"] = keys
    user.settings = settings
    session.commit()


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.get("")
async def list_api_keys(
    current_user: UserAccount = Depends(require_auth),
):
    """List all API keys for the current user.

    Requires Pro or Enterprise subscription.
    """
    # Check subscription
    if current_user.subscription_tier == SubscriptionTier.FREE:
        raise HTTPException(
            status_code=403,
            detail="API access requires Pro or Enterprise subscription"
        )

    keys = _get_user_api_keys(current_user)

    return {
        "api_keys": [
            {
                "id": k.get("id"),
                "name": k.get("name"),
                "prefix": k.get("prefix"),
                "scopes": k.get("scopes", []),
                "created_at": k.get("created_at"),
                "last_used_at": k.get("last_used_at"),
                "is_active": k.get("is_active", True),
            }
            for k in keys
        ]
    }


@router.post("", response_model=APIKeyCreatedResponse)
async def create_api_key(
    request: CreateAPIKeyRequest,
    current_user: UserAccount = Depends(require_auth),
):
    """Create a new API key.

    Requires Pro or Enterprise subscription.
    The full key is only shown once at creation time!
    """
    # Check subscription
    if current_user.subscription_tier == SubscriptionTier.FREE:
        raise HTTPException(
            status_code=403,
            detail="API access requires Pro or Enterprise subscription"
        )

    # Limit number of API keys
    existing_keys = _get_user_api_keys(current_user)
    max_keys = 5 if current_user.subscription_tier == SubscriptionTier.PRO else 20

    if len([k for k in existing_keys if k.get("is_active")]) >= max_keys:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {max_keys} API keys allowed for your subscription"
        )

    # Validate scopes
    valid_scopes = ["read", "search", "export", "lists"]
    for scope in request.scopes:
        if scope not in valid_scopes:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid scope: {scope}. Valid scopes: {valid_scopes}"
            )

    # Generate key
    api_key = _generate_api_key()
    key_hash = _hash_key(api_key)
    prefix = api_key[:12]  # scripe_XXXX

    # Create key record
    key_id = len(existing_keys) + 1
    new_key = {
        "id": key_id,
        "name": request.name,
        "key_hash": key_hash,
        "prefix": prefix,
        "scopes": request.scopes,
        "created_at": datetime.utcnow().isoformat(),
        "last_used_at": None,
        "is_active": True,
    }

    # Save
    with db.session() as session:
        user = session.query(UserAccount).filter(
            UserAccount.id == current_user.id
        ).first()
        existing_keys.append(new_key)
        _save_user_api_keys(session, user, existing_keys)

    logger.info(
        "api_key_created",
        user_id=current_user.id,
        key_name=request.name,
    )

    return APIKeyCreatedResponse(
        id=key_id,
        name=request.name,
        key=api_key,
        prefix=prefix,
        scopes=request.scopes,
    )


@router.delete("/{key_id}")
async def revoke_api_key(
    key_id: int,
    current_user: UserAccount = Depends(require_auth),
):
    """Revoke an API key.

    The key will immediately stop working.
    """
    keys = _get_user_api_keys(current_user)
    key_found = False

    for key in keys:
        if key.get("id") == key_id:
            key["is_active"] = False
            key_found = True
            break

    if not key_found:
        raise HTTPException(status_code=404, detail="API key not found")

    # Save
    with db.session() as session:
        user = session.query(UserAccount).filter(
            UserAccount.id == current_user.id
        ).first()
        _save_user_api_keys(session, user, keys)

    logger.info(
        "api_key_revoked",
        user_id=current_user.id,
        key_id=key_id,
    )

    return {"success": True, "message": "API key revoked"}


# ─── API Key Authentication Helper ───────────────────────────────────────────

async def get_user_from_api_key(
    x_api_key: str = Header(None, alias="X-API-Key"),
) -> UserAccount | None:
    """Authenticate user from API key.

    Use this as a dependency for API-key authenticated endpoints.
    """
    if not x_api_key:
        return None

    if not x_api_key.startswith("scripe_"):
        return None

    key_hash = _hash_key(x_api_key)

    with db.session() as session:
        # Search all users for matching key
        users = session.query(UserAccount).filter(
            UserAccount.is_active == True
        ).all()

        for user in users:
            keys = _get_user_api_keys(user)
            for key in keys:
                if key.get("key_hash") == key_hash and key.get("is_active"):
                    # Update last used
                    key["last_used_at"] = datetime.utcnow().isoformat()
                    _save_user_api_keys(session, user, keys)
                    return user

    return None


async def require_api_key_or_jwt(
    api_key_user: UserAccount | None = Depends(get_user_from_api_key),
    jwt_user: UserAccount | None = Depends(get_current_user),
) -> UserAccount:
    """Require either API key or JWT authentication.

    Use this for endpoints that support both auth methods.
    """
    if api_key_user:
        return api_key_user
    if jwt_user:
        return jwt_user

    raise HTTPException(
        status_code=401,
        detail="Authentication required. Provide X-API-Key header or Authorization: Bearer token"
    )
