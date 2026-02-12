"""Webhook endpoints for external services."""

from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Request, status

from app.auth.models import ProcessedWebhookEvent
from app.logging_config import get_logger
from app.storage.db import db

logger = get_logger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def is_event_processed(event_id: str, source: str) -> bool:
    """Check if a webhook event has already been processed.

    Args:
        event_id: The unique event ID from the webhook source
        source: The webhook source (e.g., "stripe")

    Returns:
        True if already processed, False otherwise
    """
    with db.session() as session:
        existing = session.query(ProcessedWebhookEvent).filter(
            ProcessedWebhookEvent.event_id == event_id,
            ProcessedWebhookEvent.source == source,
        ).first()
        return existing is not None


def mark_event_processed(event_id: str, event_type: str, source: str) -> None:
    """Mark a webhook event as processed.

    Args:
        event_id: The unique event ID from the webhook source
        event_type: The type of event (e.g., "checkout.session.completed")
        source: The webhook source (e.g., "stripe")
    """
    with db.session() as session:
        event = ProcessedWebhookEvent(
            event_id=event_id,
            event_type=event_type,
            source=source,
            processed_at=datetime.utcnow(),
        )
        session.add(event)
        session.commit()


def cleanup_old_events(days: int = 30) -> int:
    """Remove webhook events older than specified days.

    Args:
        days: Number of days to keep events

    Returns:
        Number of deleted events
    """
    cutoff = datetime.utcnow() - timedelta(days=days)
    with db.session() as session:
        deleted = session.query(ProcessedWebhookEvent).filter(
            ProcessedWebhookEvent.processed_at < cutoff
        ).delete()
        session.commit()
        return deleted


@router.post("/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events.

    Verifies the webhook signature and processes payment events.
    Uses database-backed idempotency to prevent duplicate processing.
    """
    from app.settings import settings
    from app.payments.stripe_service import (
        verify_webhook_signature,
        handle_checkout_completed,
    )

    if not settings.stripe_webhook_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Webhooks not configured",
        )

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = verify_webhook_signature(payload, sig_header)
    except ValueError as e:
        logger.warning("stripe_webhook_invalid", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    # Handle the event — with database-backed idempotency check
    event_id = event.get("id", "")
    event_type = event.get("type", "")

    if event_type == "checkout.session.completed":
        # Check for duplicate processing
        if is_event_processed(event_id, "stripe"):
            logger.info("stripe_webhook_duplicate", event_id=event_id)
            return {"received": True, "duplicate": True}

        session_data = event["data"]["object"]
        try:
            handle_checkout_completed(session_data)
            # Mark as processed AFTER successful handling
            mark_event_processed(event_id, event_type, "stripe")
            logger.info("stripe_checkout_completed", session_id=session_data["id"])
        except Exception as e:
            logger.error("stripe_checkout_error", error=str(e), session_id=session_data["id"])
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error processing payment",
            )
    else:
        logger.info("stripe_webhook_unhandled", event_type=event_type)

    return {"received": True}
