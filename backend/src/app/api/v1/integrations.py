"""CRM Integration API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.auth.middleware import require_auth
from app.auth.models import UserAccount
from app.integrations.hubspot_service import hubspot_service, HubSpotError
from app.logging_config import get_logger

router = APIRouter(prefix="/integrations", tags=["integrations"])
logger = get_logger(__name__)


# ─── Response Models ─────────────────────────────────────────────────────────

class IntegrationStatusResponse(BaseModel):
    """Status of user's integrations."""
    hubspot: dict
    # Future: salesforce, pipedrive, etc.


class HubSpotAuthResponse(BaseModel):
    """HubSpot OAuth URL response."""
    auth_url: str
    state: str


class HubSpotCallbackRequest(BaseModel):
    """HubSpot OAuth callback data."""
    code: str
    state: str


class ExportToHubSpotRequest(BaseModel):
    """Request to export leads to HubSpot."""
    search_id: int
    export_as: str = "contacts"  # "contacts" or "companies"
    lead_ids: list[int] | None = None  # Optional: specific leads to export


class ExportToHubSpotResponse(BaseModel):
    """Response from HubSpot export."""
    success: bool
    exported_count: int
    errors: list[str] = []
    hubspot_ids: list[str] = []


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.get("/status", response_model=IntegrationStatusResponse)
async def get_integration_status(
    current_user: UserAccount = Depends(require_auth),
):
    """Get status of user's CRM integrations."""
    # TODO: Check database for stored tokens
    # For now, return basic status

    hubspot_status = {
        "enabled": hubspot_service.enabled,
        "connected": False,  # TODO: Check if user has valid token
        "scopes": hubspot_service.SCOPES if hubspot_service.enabled else [],
    }

    return IntegrationStatusResponse(
        hubspot=hubspot_status,
    )


@router.get("/hubspot/auth", response_model=HubSpotAuthResponse)
async def get_hubspot_auth_url(
    current_user: UserAccount = Depends(require_auth),
):
    """Get HubSpot OAuth authorization URL.

    Redirect user to this URL to initiate HubSpot connection.
    """
    try:
        import secrets
        state = f"{current_user.id}_{secrets.token_urlsafe(16)}"
        auth_url = hubspot_service.get_auth_url(current_user.id, state)

        return HubSpotAuthResponse(
            auth_url=auth_url,
            state=state,
        )

    except HubSpotError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/hubspot/callback")
async def hubspot_oauth_callback(
    request: HubSpotCallbackRequest,
    current_user: UserAccount = Depends(require_auth),
):
    """Handle HubSpot OAuth callback.

    Exchange authorization code for access token.
    """
    try:
        # Verify state contains user ID
        state_parts = request.state.split("_", 1)
        if len(state_parts) != 2 or int(state_parts[0]) != current_user.id:
            raise HTTPException(status_code=400, detail="Invalid state parameter")

        # Exchange code for token
        token_data = await hubspot_service.exchange_code(request.code)

        # TODO: Store token in database
        # For now, return success with token info

        logger.info(
            "hubspot_connected",
            user_id=current_user.id,
        )

        return {
            "success": True,
            "message": "HubSpot connected successfully",
            "expires_in": token_data.get("expires_in"),
        }

    except HubSpotError as e:
        logger.error(
            "hubspot_callback_failed",
            user_id=current_user.id,
            error=str(e),
        )
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/hubspot/export", response_model=ExportToHubSpotResponse)
async def export_to_hubspot(
    request: ExportToHubSpotRequest,
    current_user: UserAccount = Depends(require_auth),
):
    """Export leads from a search to HubSpot.

    Requires user to have connected HubSpot account.
    """
    # TODO: Get user's HubSpot access token from database
    # For now, return not implemented

    raise HTTPException(
        status_code=501,
        detail="HubSpot export not yet implemented. Connect your HubSpot account first.",
    )


@router.delete("/hubspot/disconnect")
async def disconnect_hubspot(
    current_user: UserAccount = Depends(require_auth),
):
    """Disconnect HubSpot integration.

    Removes stored access token.
    """
    # TODO: Remove token from database

    logger.info(
        "hubspot_disconnected",
        user_id=current_user.id,
    )

    return {"success": True, "message": "HubSpot disconnected"}
