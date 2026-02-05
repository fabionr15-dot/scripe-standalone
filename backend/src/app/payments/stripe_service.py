"""Stripe payment integration for Scripe."""

import stripe
from app.auth.credits import CreditService
from app.logging_config import get_logger
from app.settings import settings

logger = get_logger(__name__)

# Initialize Stripe
stripe.api_key = settings.stripe_secret_key

credit_service = CreditService()

# Map package IDs to Stripe price metadata
PACKAGE_METADATA = {
    "starter": {"credits": 100, "bonus": 0, "price_cents": 1900, "name": "Starter - 100 Credits"},
    "growth": {"credits": 500, "bonus": 50, "price_cents": 7900, "name": "Growth - 550 Credits"},
    "scale": {"credits": 1000, "bonus": 150, "price_cents": 12900, "name": "Scale - 1,150 Credits"},
    "enterprise": {"credits": 5000, "bonus": 1000, "price_cents": 51900, "name": "Enterprise - 6,000 Credits"},
}


def create_checkout_session(
    user_id: int,
    user_email: str,
    package_id: str,
    success_url: str,
    cancel_url: str,
) -> str:
    """Create a Stripe Checkout session for credit purchase.

    Args:
        user_id: User's ID
        user_email: User's email
        package_id: Credit package ID
        success_url: URL to redirect after successful payment
        cancel_url: URL to redirect after cancelled payment

    Returns:
        Checkout session URL

    Raises:
        ValueError: If package_id is invalid or Stripe is not configured
    """
    if not settings.stripe_secret_key:
        raise ValueError("Stripe non configurato")

    package = PACKAGE_METADATA.get(package_id)
    if not package:
        raise ValueError(f"Pacchetto non valido: {package_id}")

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[
            {
                "price_data": {
                    "currency": "eur",
                    "product_data": {
                        "name": package["name"],
                        "description": f"Scripe - Pacchetto crediti per lead generation B2B",
                    },
                    "unit_amount": package["price_cents"],
                },
                "quantity": 1,
            }
        ],
        mode="payment",
        success_url=success_url,
        cancel_url=cancel_url,
        customer_email=user_email,
        metadata={
            "user_id": str(user_id),
            "package_id": package_id,
            "credits": str(package["credits"]),
            "bonus": str(package["bonus"]),
        },
    )

    logger.info(
        "checkout_session_created",
        user_id=user_id,
        package_id=package_id,
        session_id=session.id,
    )

    return session.url


def handle_checkout_completed(session: stripe.checkout.Session) -> None:
    """Handle successful checkout - add credits to user.

    Args:
        session: Completed Stripe checkout session
    """
    metadata = session.metadata
    user_id = int(metadata["user_id"])
    package_id = metadata["package_id"]

    transaction = credit_service.purchase_credits(
        user_id=user_id,
        package_id=package_id,
        payment_reference=session.payment_intent or session.id,
    )

    logger.info(
        "credits_purchased_via_stripe",
        user_id=user_id,
        package_id=package_id,
        credits_added=transaction.amount,
        payment_intent=session.payment_intent,
    )


def verify_webhook_signature(payload: bytes, sig_header: str) -> stripe.Event:
    """Verify and parse a Stripe webhook event.

    Args:
        payload: Raw request body
        sig_header: Stripe-Signature header value

    Returns:
        Verified Stripe event

    Raises:
        ValueError: If signature is invalid
    """
    if not settings.stripe_webhook_secret:
        raise ValueError("Stripe webhook secret non configurato")

    try:
        event = stripe.Webhook.construct_event(
            payload,
            sig_header,
            settings.stripe_webhook_secret,
        )
        return event
    except stripe.error.SignatureVerificationError:
        raise ValueError("Firma webhook non valida")
