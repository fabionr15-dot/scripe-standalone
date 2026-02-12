"""Referral API v1 endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from app.api.rate_limit import limiter
from app.auth.middleware import require_auth
from app.auth.models import UserAccount
from app.logging_config import get_logger
from app.referral.service import referral_service

logger = get_logger(__name__)

router = APIRouter(prefix="/referral", tags=["referral"])


# ==================== MODELS ====================


class ReferralCodeResponse(BaseModel):
    """Response with user's referral code."""
    code: str
    link: str


class ReferralStatsResponse(BaseModel):
    """Response with referral statistics."""
    code: str
    link: str
    clicks: int
    conversions: int
    credits_earned: float
    referrals_count: int


class ValidateCodeRequest(BaseModel):
    """Request to validate a referral code."""
    code: str


class ValidateCodeResponse(BaseModel):
    """Response from code validation."""
    valid: bool
    referrer_name: str | None = None
    bonus_credits: int = 20


class TrackClickRequest(BaseModel):
    """Request to track a referral link click."""
    code: str


# ==================== ENDPOINTS ====================


@router.get("/code", response_model=ReferralCodeResponse)
async def get_referral_code(user: UserAccount = Depends(require_auth)):
    """Get current user's referral code.

    Creates a new code if user doesn't have one.
    """
    referral_code = referral_service.get_or_create_code(user.id)

    return ReferralCodeResponse(
        code=referral_code.code,
        link=f"https://scripe.fabioprivato.org/ref/{referral_code.code}",
    )


@router.get("/stats", response_model=ReferralStatsResponse)
async def get_referral_stats(user: UserAccount = Depends(require_auth)):
    """Get referral statistics for current user.

    Includes:
    - Total clicks on referral link
    - Number of successful conversions
    - Total credits earned from referrals
    - Commission earned from referred users' purchases
    """
    stats = referral_service.get_referral_stats(user.id)

    return ReferralStatsResponse(**stats)


@router.post("/validate", response_model=ValidateCodeResponse)
@limiter.limit("30/minute")
async def validate_referral_code(request: Request, body: ValidateCodeRequest):
    """Validate a referral code.

    Used during registration to check if a referral code is valid
    and get the referrer's name for personalization.
    """
    referral_code = referral_service.validate_code(body.code)

    if not referral_code:
        return ValidateCodeResponse(valid=False)

    # Get referrer's name (first name only for privacy)
    from app.storage.db import db
    with db.session() as session:
        referrer = session.query(UserAccount).filter(
            UserAccount.id == referral_code.user_id
        ).first()
        referrer_name = referrer.name.split()[0] if referrer and referrer.name else None

    return ValidateCodeResponse(
        valid=True,
        referrer_name=referrer_name,
        bonus_credits=20,
    )


@router.post("/track-click")
@limiter.limit("60/minute")
async def track_referral_click(request: Request, body: TrackClickRequest):
    """Track a click on a referral link.

    Called when someone visits scripe.io/ref/CODE.
    """
    success = referral_service.track_click(body.code)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid referral code",
        )

    return {"success": True}


@router.get("/link")
async def get_shareable_link(user: UserAccount = Depends(require_auth)):
    """Get shareable referral link for current user.

    Returns various formats for sharing:
    - Direct link
    - Text with link for messaging
    - HTML for email
    """
    referral_code = referral_service.get_or_create_code(user.id)
    link = f"https://scripe.fabioprivato.org/ref/{referral_code.code}"

    user_name = user.name or "Ein Freund"

    return {
        "link": link,
        "code": referral_code.code,
        "share_text": f"{user_name} schenkt dir 20 Credits! Registriere dich mit diesem Link: {link}",
        "share_text_en": f"{user_name} is giving you 20 free credits! Sign up here: {link}",
        "email_subject": "Du hast 20 kostenlose Credits auf Scripe!",
        "email_body": f"""
Hallo!

{user_name} hat dich zu Scripe eingeladen und schenkt dir 20 kostenlose Credits!

Scripe ist eine B2B Lead-Generation Plattform. Mit deinen 20 Credits kannst du sofort starten.

Jetzt registrieren: {link}

Viel Erfolg!
""".strip(),
    }
