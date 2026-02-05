"""Webhook endpoints for external services."""

from fastapi import APIRouter, HTTPException, Request, status

from app.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events.

    Verifies the webhook signature and processes payment events.
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

    # Handle the event
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        try:
            handle_checkout_completed(session)
            logger.info("stripe_checkout_completed", session_id=session["id"])
        except Exception as e:
            logger.error("stripe_checkout_error", error=str(e), session_id=session["id"])
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error processing payment",
            )
    else:
        logger.info("stripe_webhook_unhandled", event_type=event["type"])

    return {"received": True}
