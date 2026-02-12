"""Referral system database models."""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.storage.db import Base


class ReferralCode(Base):
    """Unique referral code for each user.

    Each user gets one referral code that they can share.
    Tracks clicks, conversions, and total credits earned from signup bonuses.
    """
    __tablename__ = "referral_codes"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("user_accounts.id"), nullable=False, unique=True)
    code = Column(String(20), unique=True, nullable=False, index=True)

    # Statistics
    clicks = Column(Integer, default=0)  # How many times the link was visited
    conversions = Column(Integer, default=0)  # How many users registered with this code
    credits_earned = Column(Float, default=0.0)  # Total credits earned from signup bonuses

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("UserAccount", foreign_keys=[user_id])
    referrals = relationship("Referral", back_populates="referral_code")

    def __repr__(self):
        return f"<ReferralCode(code={self.code}, conversions={self.conversions})>"


class Referral(Base):
    """Individual referral record.

    Tracks each referral relationship between users.
    """
    __tablename__ = "referrals"

    id = Column(Integer, primary_key=True)
    referrer_id = Column(Integer, ForeignKey("user_accounts.id"), nullable=False, index=True)
    referred_id = Column(Integer, ForeignKey("user_accounts.id"), nullable=False, unique=True)
    referral_code_id = Column(Integer, ForeignKey("referral_codes.id"), nullable=False)

    # Status
    signup_bonus_credited = Column(Boolean, default=False)  # 20 credits on signup
    is_active = Column(Boolean, default=True)  # Can be deactivated for fraud

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    referrer = relationship("UserAccount", foreign_keys=[referrer_id])
    referred = relationship("UserAccount", foreign_keys=[referred_id])
    referral_code = relationship("ReferralCode", back_populates="referrals")

    def __repr__(self):
        return f"<Referral(referrer={self.referrer_id}, referred={self.referred_id})>"
