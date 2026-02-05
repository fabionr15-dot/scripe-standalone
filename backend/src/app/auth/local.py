"""Local authentication service (email/password)."""

from datetime import datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.auth.models import AuthProvider, UserAccount, SubscriptionTier
from app.logging_config import get_logger
from app.settings import settings
from app.storage.db import db

logger = get_logger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
JWT_SECRET_KEY = settings.jwt_secret_key
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 2  # Reduced from 24h for security


class LocalAuthService:
    """Authentication service for local (email/password) users."""

    def __init__(self):
        """Initialize auth service."""
        self.logger = get_logger(__name__)

    # ==================== PASSWORD ====================

    def _truncate_password(self, password: str) -> str:
        """Truncate password to 72 bytes (bcrypt limit).

        Args:
            password: Plain password

        Returns:
            Truncated password
        """
        return password.encode('utf-8')[:72].decode('utf-8', errors='ignore')

    def hash_password(self, password: str) -> str:
        """Hash a password.

        Args:
            password: Plain password

        Returns:
            Hashed password
        """
        return pwd_context.hash(self._truncate_password(password))

    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify a password against hash.

        Args:
            password: Plain password
            hashed: Hashed password

        Returns:
            True if matches
        """
        return pwd_context.verify(self._truncate_password(password), hashed)

    # ==================== USER MANAGEMENT ====================

    def create_user(
        self,
        email: str,
        password: str,
        name: str | None = None,
    ) -> UserAccount:
        """Create a new local user.

        Args:
            email: User email
            password: Plain password
            name: Optional name

        Returns:
            Created user account

        Raises:
            ValueError: If email already exists
        """
        with db.session() as session:
            # Check if email exists
            existing = session.query(UserAccount).filter(
                UserAccount.email == email.lower()
            ).first()

            if existing:
                raise ValueError("Email already registered")

            # Create user
            user = UserAccount(
                email=email.lower(),
                name=name,
                auth_provider=AuthProvider.LOCAL,
                password_hash=self.hash_password(password),
                subscription_tier=SubscriptionTier.FREE,
                credits_balance=10.0,  # Welcome credits
            )
            session.add(user)
            session.commit()
            session.refresh(user)

            self.logger.info("user_created", user_id=user.id, email=email)
            return user

    def authenticate(self, email: str, password: str) -> UserAccount | None:
        """Authenticate a user.

        Args:
            email: User email
            password: Plain password

        Returns:
            User account if valid, None otherwise
        """
        with db.session() as session:
            user = session.query(UserAccount).filter(
                UserAccount.email == email.lower(),
                UserAccount.auth_provider == AuthProvider.LOCAL,
                UserAccount.is_active == True,
            ).first()

            if not user:
                return None

            if not user.password_hash:
                return None

            if not self.verify_password(password, user.password_hash):
                return None

            # Update last login
            user.last_login_at = datetime.utcnow()
            session.commit()

            self.logger.info("user_authenticated", user_id=user.id)
            return user

    def get_user_by_id(self, user_id: int) -> UserAccount | None:
        """Get user by ID.

        Args:
            user_id: User ID

        Returns:
            User account or None
        """
        with db.session() as session:
            return session.query(UserAccount).filter(
                UserAccount.id == user_id,
                UserAccount.is_active == True,
            ).first()

    def get_user_by_email(self, email: str) -> UserAccount | None:
        """Get user by email.

        Args:
            email: User email

        Returns:
            User account or None
        """
        with db.session() as session:
            return session.query(UserAccount).filter(
                UserAccount.email == email.lower(),
            ).first()

    def update_user(
        self,
        user_id: int,
        name: str | None = None,
        settings: dict | None = None,
    ) -> UserAccount | None:
        """Update user profile.

        Args:
            user_id: User ID
            name: New name
            settings: New settings

        Returns:
            Updated user or None
        """
        with db.session() as session:
            user = session.query(UserAccount).filter(
                UserAccount.id == user_id
            ).first()

            if not user:
                return None

            if name is not None:
                user.name = name
            if settings is not None:
                user.settings = settings

            user.updated_at = datetime.utcnow()
            session.commit()
            session.refresh(user)

            return user

    def change_password(
        self,
        user_id: int,
        old_password: str,
        new_password: str,
    ) -> bool:
        """Change user password.

        Args:
            user_id: User ID
            old_password: Current password
            new_password: New password

        Returns:
            True if changed successfully
        """
        with db.session() as session:
            user = session.query(UserAccount).filter(
                UserAccount.id == user_id,
                UserAccount.auth_provider == AuthProvider.LOCAL,
            ).first()

            if not user or not user.password_hash:
                return False

            if not self.verify_password(old_password, user.password_hash):
                return False

            user.password_hash = self.hash_password(new_password)
            user.updated_at = datetime.utcnow()
            session.commit()

            self.logger.info("password_changed", user_id=user_id)
            return True

    # ==================== JWT TOKENS ====================

    def create_access_token(
        self,
        user: UserAccount,
        expires_delta: timedelta | None = None,
    ) -> str:
        """Create JWT access token.

        Args:
            user: User account
            expires_delta: Optional expiration time

        Returns:
            JWT token string
        """
        if expires_delta is None:
            expires_delta = timedelta(hours=JWT_EXPIRE_HOURS)

        expire = datetime.utcnow() + expires_delta

        payload = {
            "sub": str(user.id),
            "email": user.email,
            "provider": user.auth_provider.value,
            "tier": user.subscription_tier.value,
            "exp": expire,
            "iat": datetime.utcnow(),
        }

        token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        return token

    def verify_token(self, token: str) -> dict[str, Any] | None:
        """Verify and decode JWT token.

        Args:
            token: JWT token string

        Returns:
            Token payload or None if invalid
        """
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            return payload
        except JWTError as e:
            self.logger.debug("token_verification_failed", error=str(e))
            return None

    def get_user_from_token(self, token: str) -> UserAccount | None:
        """Get user from JWT token.

        Args:
            token: JWT token string

        Returns:
            User account or None
        """
        payload = self.verify_token(token)
        if not payload:
            return None

        user_id = payload.get("sub")
        if not user_id:
            return None

        return self.get_user_by_id(int(user_id))

    # ==================== EMAIL VERIFICATION ====================

    def generate_verification_token(self, user_id: int) -> str:
        """Generate email verification token.

        Args:
            user_id: User ID

        Returns:
            Verification token
        """
        payload = {
            "sub": str(user_id),
            "type": "email_verification",
            "exp": datetime.utcnow() + timedelta(hours=24),
        }
        return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

    def verify_email(self, token: str) -> bool:
        """Verify email with token.

        Args:
            token: Verification token

        Returns:
            True if verified successfully
        """
        payload = self.verify_token(token)
        if not payload or payload.get("type") != "email_verification":
            return False

        user_id = payload.get("sub")
        if not user_id:
            return False

        with db.session() as session:
            user = session.query(UserAccount).filter(
                UserAccount.id == int(user_id)
            ).first()

            if not user:
                return False

            user.email_verified = True
            user.updated_at = datetime.utcnow()
            session.commit()

            self.logger.info("email_verified", user_id=user_id)
            return True

    # ==================== PASSWORD RESET ====================

    def generate_reset_token(self, email: str) -> str | None:
        """Generate password reset token.

        Args:
            email: User email

        Returns:
            Reset token or None if user not found
        """
        user = self.get_user_by_email(email)
        if not user or user.auth_provider != AuthProvider.LOCAL:
            return None

        payload = {
            "sub": str(user.id),
            "type": "password_reset",
            "exp": datetime.utcnow() + timedelta(hours=1),
        }
        return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

    def reset_password(self, token: str, new_password: str) -> bool:
        """Reset password with token.

        Args:
            token: Reset token
            new_password: New password

        Returns:
            True if reset successfully
        """
        payload = self.verify_token(token)
        if not payload or payload.get("type") != "password_reset":
            return False

        user_id = payload.get("sub")
        if not user_id:
            return False

        with db.session() as session:
            user = session.query(UserAccount).filter(
                UserAccount.id == int(user_id),
                UserAccount.auth_provider == AuthProvider.LOCAL,
            ).first()

            if not user:
                return False

            user.password_hash = self.hash_password(new_password)
            user.updated_at = datetime.utcnow()
            session.commit()

            self.logger.info("password_reset", user_id=user_id)
            return True
