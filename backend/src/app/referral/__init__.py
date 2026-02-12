"""Referral system module for Scripe.

Simple signup bonus system:
- Referrer gets 20 credits when someone signs up with their code
- Referred user gets 20 extra credits (30 total instead of 10)
"""

from app.referral.models import ReferralCode, Referral
from app.referral.service import ReferralService, referral_service

__all__ = ["ReferralCode", "Referral", "ReferralService", "referral_service"]
