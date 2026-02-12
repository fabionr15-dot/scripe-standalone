"""Referral service for managing referral codes and signup bonuses."""

import secrets
import string
from datetime import datetime
from typing import Any

from app.auth.models import UserAccount
from app.logging_config import get_logger
from app.referral.models import ReferralCode, Referral
from app.storage.db import db

logger = get_logger(__name__)

# Signup bonus for both referrer and referred
REFERRER_SIGNUP_BONUS = 20.0  # Credits referrer gets when someone signs up
REFERRED_SIGNUP_BONUS = 20.0  # Extra credits for new user (on top of normal 10)


def _generate_unique_code(length: int = 8) -> str:
    """Generate a unique, readable referral code.

    Uses uppercase letters and digits, avoiding confusing characters.
    Format: ABC12XYZ (8 chars by default)
    """
    # Exclude confusing characters: 0, O, I, l, 1
    alphabet = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))


class ReferralService:
    """Service for managing referral codes and commissions."""

    def __init__(self):
        """Initialize referral service."""
        self.logger = get_logger(__name__)

    def get_or_create_code(self, user_id: int) -> ReferralCode:
        """Get existing referral code or create new one for user.

        Args:
            user_id: User ID

        Returns:
            ReferralCode object
        """
        with db.session() as session:
            # Check if user already has a code
            existing = session.query(ReferralCode).filter(
                ReferralCode.user_id == user_id
            ).first()

            if existing:
                return existing

            # Generate unique code
            code = _generate_unique_code()
            attempts = 0
            while attempts < 10:
                existing_code = session.query(ReferralCode).filter(
                    ReferralCode.code == code
                ).first()
                if not existing_code:
                    break
                code = _generate_unique_code()
                attempts += 1

            # Create new code
            referral_code = ReferralCode(
                user_id=user_id,
                code=code,
            )
            session.add(referral_code)
            session.commit()
            session.refresh(referral_code)

            self.logger.info(
                "referral_code_created",
                user_id=user_id,
                code=code,
            )

            return referral_code

    def validate_code(self, code: str) -> ReferralCode | None:
        """Validate a referral code.

        Args:
            code: Referral code to validate

        Returns:
            ReferralCode if valid, None otherwise
        """
        if not code:
            return None

        code = code.upper().strip()

        with db.session() as session:
            referral_code = session.query(ReferralCode).filter(
                ReferralCode.code == code
            ).first()

            return referral_code

    def track_click(self, code: str) -> bool:
        """Track a click on referral link.

        Args:
            code: Referral code

        Returns:
            True if tracked successfully
        """
        code = code.upper().strip()

        with db.session() as session:
            referral_code = session.query(ReferralCode).filter(
                ReferralCode.code == code
            ).first()

            if not referral_code:
                return False

            referral_code.clicks += 1
            referral_code.updated_at = datetime.utcnow()
            session.commit()

            self.logger.info("referral_click_tracked", code=code)
            return True

    def process_signup(
        self,
        referrer_id: int,
        referred_id: int,
        referral_code_id: int,
    ) -> Referral:
        """Process a successful referral signup.

        Creates referral record and credits both users.

        Args:
            referrer_id: ID of user who referred
            referred_id: ID of new user who signed up
            referral_code_id: ID of the referral code used

        Returns:
            Referral record
        """
        from app.auth.credits import CreditService
        credit_service = CreditService()

        with db.session() as session:
            # Create referral record
            referral = Referral(
                referrer_id=referrer_id,
                referred_id=referred_id,
                referral_code_id=referral_code_id,
                signup_bonus_credited=True,
            )
            session.add(referral)

            # Update referral code stats
            referral_code = session.query(ReferralCode).filter(
                ReferralCode.id == referral_code_id
            ).first()
            if referral_code:
                referral_code.conversions += 1
                referral_code.credits_earned += REFERRER_SIGNUP_BONUS
                referral_code.updated_at = datetime.utcnow()

            session.commit()
            session.refresh(referral)

        # Credit referrer with signup bonus (outside transaction for clean logging)
        credit_service.add_credits(
            user_id=referrer_id,
            amount=REFERRER_SIGNUP_BONUS,
            operation="referral_bonus",
            description=f"Referral signup bonus - new user registered with your code",
            metadata={
                "referral_id": referral.id,
                "referred_user_id": referred_id,
                "bonus_type": "signup",
            },
        )

        self.logger.info(
            "referral_signup_processed",
            referrer_id=referrer_id,
            referred_id=referred_id,
            bonus_credited=REFERRER_SIGNUP_BONUS,
        )

        return referral

    def get_referral_stats(self, user_id: int) -> dict[str, Any]:
        """Get referral statistics for a user.

        Args:
            user_id: User ID

        Returns:
            Dict with referral stats
        """
        with db.session() as session:
            referral_code = session.query(ReferralCode).filter(
                ReferralCode.user_id == user_id
            ).first()

            if not referral_code:
                # Create code if doesn't exist
                referral_code = self.get_or_create_code(user_id)

            # Get list of referred users
            referrals = session.query(Referral).filter(
                Referral.referrer_id == user_id,
            ).all()

            return {
                "code": referral_code.code,
                "link": f"https://scripe.fabioprivato.org/ref/{referral_code.code}",
                "clicks": referral_code.clicks,
                "conversions": referral_code.conversions,
                "credits_earned": referral_code.credits_earned,
                "referrals_count": len(referrals),
            }

    def get_referrer_for_user(self, user_id: int) -> int | None:
        """Get the referrer ID for a user.

        Args:
            user_id: User ID to check

        Returns:
            Referrer's user ID or None
        """
        with db.session() as session:
            referral = session.query(Referral).filter(
                Referral.referred_id == user_id,
            ).first()

            return referral.referrer_id if referral else None


# Singleton instance
referral_service = ReferralService()
