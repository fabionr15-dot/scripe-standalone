"""Credit management system for Scripe."""

from datetime import datetime
from typing import Any

from app.auth.models import CreditTransaction, UserAccount
from app.logging_config import get_logger
from app.storage.db import db

logger = get_logger(__name__)


class InsufficientCreditsError(Exception):
    """Raised when user has insufficient credits."""

    def __init__(self, required: float, available: float):
        self.required = required
        self.available = available
        super().__init__(f"Insufficient credits: required {required}, available {available}")


class CreditService:
    """Service for managing user credits.

    Operations:
    - Purchase credits
    - Spend credits on searches
    - Refund credits
    - Bonus credits
    """

    # Credit packages for purchase
    CREDIT_PACKAGES = {
        "starter": {"credits": 100, "price_eur": 10.0, "bonus": 0},
        "growth": {"credits": 500, "price_eur": 40.0, "bonus": 50},  # 10% bonus
        "scale": {"credits": 1000, "price_eur": 70.0, "bonus": 150},  # 15% bonus
        "enterprise": {"credits": 5000, "price_eur": 300.0, "bonus": 1000},  # 20% bonus
    }

    def __init__(self):
        """Initialize credit service."""
        self.logger = get_logger(__name__)

    def get_balance(self, user_id: int) -> float:
        """Get user's credit balance.

        Args:
            user_id: User ID

        Returns:
            Credit balance
        """
        with db.session() as session:
            user = session.query(UserAccount).filter(
                UserAccount.id == user_id
            ).first()

            if not user:
                return 0.0

            return user.credits_balance

    def has_credits(self, user_id: int, amount: float) -> bool:
        """Check if user has sufficient credits.

        Args:
            user_id: User ID
            amount: Required amount

        Returns:
            True if sufficient
        """
        return self.get_balance(user_id) >= amount

    def add_credits(
        self,
        user_id: int,
        amount: float,
        operation: str,
        description: str | None = None,
        metadata: dict | None = None,
    ) -> CreditTransaction:
        """Add credits to user account.

        Args:
            user_id: User ID
            amount: Amount to add (positive)
            operation: Operation type (purchase, refund, bonus)
            description: Optional description
            metadata: Optional metadata

        Returns:
            Credit transaction record
        """
        if amount <= 0:
            raise ValueError("Amount must be positive")

        with db.session() as session:
            user = session.query(UserAccount).filter(
                UserAccount.id == user_id
            ).first()

            if not user:
                raise ValueError(f"User {user_id} not found")

            # Update balance
            new_balance = user.credits_balance + amount
            user.credits_balance = new_balance
            user.updated_at = datetime.utcnow()

            # Create transaction record
            import json
            transaction = CreditTransaction(
                user_id=user_id,
                amount=amount,
                balance_after=new_balance,
                operation=operation,
                description=description,
                metadata_json=json.dumps(metadata) if metadata else None,
            )
            session.add(transaction)
            session.commit()
            session.refresh(transaction)

            self.logger.info(
                "credits_added",
                user_id=user_id,
                amount=amount,
                operation=operation,
                new_balance=new_balance,
            )

            return transaction

    def spend_credits(
        self,
        user_id: int,
        amount: float,
        operation: str = "search",
        search_id: int | None = None,
        description: str | None = None,
    ) -> CreditTransaction:
        """Spend credits from user account.

        Args:
            user_id: User ID
            amount: Amount to spend (positive)
            operation: Operation type
            search_id: Optional search ID reference
            description: Optional description

        Returns:
            Credit transaction record

        Raises:
            InsufficientCreditsError: If not enough credits
        """
        if amount <= 0:
            raise ValueError("Amount must be positive")

        with db.session() as session:
            user = session.query(UserAccount).filter(
                UserAccount.id == user_id
            ).first()

            if not user:
                raise ValueError(f"User {user_id} not found")

            if user.credits_balance < amount:
                raise InsufficientCreditsError(amount, user.credits_balance)

            # Update balance
            new_balance = user.credits_balance - amount
            user.credits_balance = new_balance
            user.credits_used_total += amount
            user.updated_at = datetime.utcnow()

            # Create transaction record
            transaction = CreditTransaction(
                user_id=user_id,
                amount=-amount,  # Negative for spending
                balance_after=new_balance,
                operation=operation,
                search_id=search_id,
                description=description,
            )
            session.add(transaction)
            session.commit()
            session.refresh(transaction)

            self.logger.info(
                "credits_spent",
                user_id=user_id,
                amount=amount,
                search_id=search_id,
                new_balance=new_balance,
            )

            return transaction

    def refund_credits(
        self,
        user_id: int,
        amount: float,
        search_id: int | None = None,
        reason: str | None = None,
    ) -> CreditTransaction:
        """Refund credits to user account.

        Args:
            user_id: User ID
            amount: Amount to refund
            search_id: Related search ID
            reason: Refund reason

        Returns:
            Credit transaction record
        """
        return self.add_credits(
            user_id=user_id,
            amount=amount,
            operation="refund",
            description=reason or f"Refund for search {search_id}" if search_id else "Refund",
            metadata={"search_id": search_id} if search_id else None,
        )

    def purchase_credits(
        self,
        user_id: int,
        package_id: str,
        payment_reference: str | None = None,
    ) -> CreditTransaction:
        """Purchase credit package.

        Args:
            user_id: User ID
            package_id: Package identifier
            payment_reference: Payment reference (e.g., Stripe ID)

        Returns:
            Credit transaction record

        Raises:
            ValueError: If invalid package
        """
        package = self.CREDIT_PACKAGES.get(package_id)
        if not package:
            raise ValueError(f"Invalid package: {package_id}")

        total_credits = package["credits"] + package["bonus"]

        return self.add_credits(
            user_id=user_id,
            amount=total_credits,
            operation="purchase",
            description=f"Purchased {package_id} package ({package['credits']} + {package['bonus']} bonus credits)",
            metadata={
                "package_id": package_id,
                "base_credits": package["credits"],
                "bonus_credits": package["bonus"],
                "price_eur": package["price_eur"],
                "payment_reference": payment_reference,
            },
        )

    def add_welcome_bonus(self, user_id: int) -> CreditTransaction:
        """Add welcome bonus for new users.

        Args:
            user_id: User ID

        Returns:
            Credit transaction record
        """
        return self.add_credits(
            user_id=user_id,
            amount=10.0,
            operation="bonus",
            description="Welcome bonus credits",
            metadata={"bonus_type": "welcome"},
        )

    def get_transaction_history(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> list[CreditTransaction]:
        """Get user's transaction history.

        Args:
            user_id: User ID
            limit: Max records
            offset: Offset for pagination

        Returns:
            List of transactions
        """
        with db.session() as session:
            return session.query(CreditTransaction).filter(
                CreditTransaction.user_id == user_id
            ).order_by(
                CreditTransaction.created_at.desc()
            ).offset(offset).limit(limit).all()

    def get_usage_summary(self, user_id: int) -> dict[str, Any]:
        """Get credit usage summary.

        Args:
            user_id: User ID

        Returns:
            Usage summary dict
        """
        with db.session() as session:
            user = session.query(UserAccount).filter(
                UserAccount.id == user_id
            ).first()

            if not user:
                return {}

            # Get transaction stats
            from sqlalchemy import func

            total_purchased = session.query(
                func.sum(CreditTransaction.amount)
            ).filter(
                CreditTransaction.user_id == user_id,
                CreditTransaction.operation == "purchase",
            ).scalar() or 0

            total_spent = session.query(
                func.sum(CreditTransaction.amount)
            ).filter(
                CreditTransaction.user_id == user_id,
                CreditTransaction.operation == "search",
            ).scalar() or 0

            total_refunded = session.query(
                func.sum(CreditTransaction.amount)
            ).filter(
                CreditTransaction.user_id == user_id,
                CreditTransaction.operation == "refund",
            ).scalar() or 0

            search_count = session.query(
                func.count(CreditTransaction.id)
            ).filter(
                CreditTransaction.user_id == user_id,
                CreditTransaction.operation == "search",
            ).scalar() or 0

            return {
                "current_balance": user.credits_balance,
                "total_purchased": abs(total_purchased),
                "total_spent": abs(total_spent),
                "total_refunded": abs(total_refunded),
                "total_used": user.credits_used_total,
                "search_count": search_count,
                "avg_per_search": user.credits_used_total / search_count if search_count > 0 else 0,
            }

    @classmethod
    def get_packages(cls) -> list[dict[str, Any]]:
        """Get available credit packages.

        Returns:
            List of package info
        """
        packages = []
        for package_id, info in cls.CREDIT_PACKAGES.items():
            packages.append({
                "id": package_id,
                "credits": info["credits"],
                "bonus": info["bonus"],
                "total": info["credits"] + info["bonus"],
                "price_eur": info["price_eur"],
                "price_per_credit": info["price_eur"] / (info["credits"] + info["bonus"]),
            })
        return packages
