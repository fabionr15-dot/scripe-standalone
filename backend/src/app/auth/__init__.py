"""Authentication system for Scripe - supports dual auth (Zitadel + Local)."""

from app.auth.models import User, UserAccount, AuthProvider
from app.auth.local import LocalAuthService
from app.auth.middleware import get_current_user, require_auth
from app.auth.credits import CreditService

__all__ = [
    "User",
    "UserAccount",
    "AuthProvider",
    "LocalAuthService",
    "CreditService",
    "get_current_user",
    "require_auth",
]
