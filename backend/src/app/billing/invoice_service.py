"""Invoice service for creating and managing invoices."""

import json
from datetime import datetime
from decimal import Decimal
from typing import Any

import structlog
from sqlalchemy.orm import Session

from app.billing.models import BillingAddress, Invoice, InvoiceStatus
from app.auth.models import UserAccount
from app.storage.db import get_db

logger = structlog.get_logger()


class InvoiceService:
    """Service for managing invoices."""

    # Default tax rate for EU (can be overridden)
    DEFAULT_TAX_RATE = Decimal("19.00")  # 19% German VAT

    def __init__(self, db: Session | None = None):
        self.db = db or next(get_db())

    def generate_invoice_number(self) -> str:
        """Generate a unique invoice number.

        Format: INV-YYYY-NNNNN
        Example: INV-2026-00001
        """
        year = datetime.utcnow().year

        # Get the last invoice number for this year
        last_invoice = (
            self.db.query(Invoice)
            .filter(Invoice.invoice_number.like(f"INV-{year}-%"))
            .order_by(Invoice.id.desc())
            .first()
        )

        if last_invoice:
            # Extract sequence number and increment
            try:
                last_seq = int(last_invoice.invoice_number.split("-")[-1])
                next_seq = last_seq + 1
            except (ValueError, IndexError):
                next_seq = 1
        else:
            next_seq = 1

        return f"INV-{year}-{next_seq:05d}"

    def create_invoice_for_purchase(
        self,
        user: UserAccount,
        amount: Decimal,
        package_name: str,
        credits: int,
        stripe_checkout_session_id: str | None = None,
        stripe_payment_intent_id: str | None = None,
    ) -> Invoice:
        """Create an invoice after a successful purchase.

        Args:
            user: The user who made the purchase
            amount: Total amount paid (in EUR)
            package_name: Name of the credit package
            credits: Number of credits purchased
            stripe_checkout_session_id: Stripe checkout session ID
            stripe_payment_intent_id: Stripe payment intent ID

        Returns:
            Created Invoice instance
        """
        # Determine tax rate
        # If user has VAT ID and is in EU, apply reverse charge (0% tax)
        # Otherwise apply standard tax rate
        if user.vat_id and user.tax_exempt:
            tax_rate = Decimal("0.00")
            tax_note = "Reverse Charge - VAT exempt"
        else:
            tax_rate = self.DEFAULT_TAX_RATE
            tax_note = None

        # Calculate amounts
        # Amount from Stripe is the total paid, so we need to work backwards
        total = Decimal(str(amount))
        if tax_rate > 0:
            # Total = Subtotal * (1 + tax_rate/100)
            subtotal = total / (1 + tax_rate / 100)
            tax_amount = total - subtotal
        else:
            subtotal = total
            tax_amount = Decimal("0.00")

        # Round to 2 decimal places
        subtotal = subtotal.quantize(Decimal("0.01"))
        tax_amount = tax_amount.quantize(Decimal("0.01"))

        # Create invoice items
        items = [
            {
                "description": f"{package_name} - {credits} Credits",
                "quantity": 1,
                "unit_price": float(subtotal),
                "amount": float(subtotal),
            }
        ]

        # Get billing address snapshot
        primary_address = (
            self.db.query(BillingAddress)
            .filter(BillingAddress.user_id == user.id, BillingAddress.is_primary == True)
            .first()
        )

        billing_address_snapshot = primary_address.to_dict() if primary_address else None

        # Customer snapshot
        customer_snapshot = {
            "name": user.name or user.email,
            "email": user.billing_email or user.email,
            "company_name": user.company_name,
            "vat_id": user.vat_id,
        }

        # Create invoice
        invoice = Invoice(
            user_id=user.id,
            invoice_number=self.generate_invoice_number(),
            invoice_date=datetime.utcnow(),
            subtotal=subtotal,
            tax_rate=tax_rate,
            tax_amount=tax_amount,
            total=total,
            currency="EUR",
            status=InvoiceStatus.PAID.value,
            stripe_checkout_session_id=stripe_checkout_session_id,
            stripe_payment_intent_id=stripe_payment_intent_id,
            items_json=json.dumps(items),
            billing_address_snapshot=json.dumps(billing_address_snapshot) if billing_address_snapshot else None,
            customer_snapshot=json.dumps(customer_snapshot),
            notes=tax_note,
        )

        self.db.add(invoice)
        self.db.commit()
        self.db.refresh(invoice)

        logger.info(
            "invoice_created",
            invoice_id=invoice.id,
            invoice_number=invoice.invoice_number,
            user_id=user.id,
            total=float(total),
        )

        return invoice

    def get_user_invoices(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Invoice], int]:
        """Get all invoices for a user.

        Args:
            user_id: User ID
            limit: Maximum number of invoices to return
            offset: Number of invoices to skip

        Returns:
            Tuple of (list of invoices, total count)
        """
        query = self.db.query(Invoice).filter(Invoice.user_id == user_id)

        total = query.count()

        invoices = (
            query
            .order_by(Invoice.invoice_date.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        return invoices, total

    def get_invoice_by_id(self, invoice_id: int, user_id: int) -> Invoice | None:
        """Get a specific invoice by ID.

        IDOR Protection: Always filter by user_id!

        Args:
            invoice_id: Invoice ID
            user_id: User ID (for security)

        Returns:
            Invoice if found and belongs to user, None otherwise
        """
        return (
            self.db.query(Invoice)
            .filter(Invoice.id == invoice_id, Invoice.user_id == user_id)
            .first()
        )

    def get_invoice_by_number(self, invoice_number: str, user_id: int) -> Invoice | None:
        """Get a specific invoice by number.

        IDOR Protection: Always filter by user_id!

        Args:
            invoice_number: Invoice number (e.g., INV-2026-00001)
            user_id: User ID (for security)

        Returns:
            Invoice if found and belongs to user, None otherwise
        """
        return (
            self.db.query(Invoice)
            .filter(Invoice.invoice_number == invoice_number, Invoice.user_id == user_id)
            .first()
        )


# Singleton instance
_invoice_service: InvoiceService | None = None


def get_invoice_service(db: Session | None = None) -> InvoiceService:
    """Get or create InvoiceService instance."""
    global _invoice_service
    if _invoice_service is None or db is not None:
        _invoice_service = InvoiceService(db)
    return _invoice_service
