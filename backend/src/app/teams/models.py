"""Team account database models."""

from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship

from app.storage.db import Base


class TeamRole(str, Enum):
    """Team member roles."""
    OWNER = "owner"      # Full control, billing, can delete team
    ADMIN = "admin"      # Can manage members, use credits
    MEMBER = "member"    # Can use credits, view shared content


class Team(Base):
    """Team account for collaborative lead generation.

    Teams have:
    - Shared credit pool
    - Multiple members with different roles
    - Shared searches and lists
    """
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True)

    # Team info
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)  # URL-friendly identifier
    description = Column(Text, nullable=True)

    # Owner (always the creator)
    owner_id = Column(Integer, ForeignKey("user_accounts.id"), nullable=False)

    # Credits
    credits_balance = Column(Float, default=0.0)
    credits_used_total = Column(Float, default=0.0)

    # Limits
    max_members = Column(Integer, default=5)  # Can be increased with subscription

    # Subscription
    subscription_tier = Column(String(50), default="team_basic")  # team_basic, team_pro, enterprise
    subscription_expires_at = Column(DateTime, nullable=True)

    # Settings
    settings_json = Column(Text, nullable=True)

    # Status
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    owner = relationship("UserAccount", foreign_keys=[owner_id])
    members = relationship("TeamMember", back_populates="team", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Team(id={self.id}, name={self.name}, members={len(self.members)})>"


class TeamMember(Base):
    """Team membership record.

    Links users to teams with specific roles.
    """
    __tablename__ = "team_members"

    id = Column(Integer, primary_key=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("user_accounts.id"), nullable=False, index=True)

    # Role
    role = Column(SQLEnum(TeamRole), default=TeamRole.MEMBER)

    # Invitation
    invited_by_id = Column(Integer, ForeignKey("user_accounts.id"), nullable=True)
    invitation_token = Column(String(64), nullable=True, unique=True)
    invitation_email = Column(String(255), nullable=True)  # For pending invites
    accepted_at = Column(DateTime, nullable=True)

    # Status
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    team = relationship("Team", back_populates="members")
    user = relationship("UserAccount", foreign_keys=[user_id])
    invited_by = relationship("UserAccount", foreign_keys=[invited_by_id])

    def __repr__(self):
        return f"<TeamMember(team={self.team_id}, user={self.user_id}, role={self.role})>"


class TeamCreditTransaction(Base):
    """Credit transaction for team account."""
    __tablename__ = "team_credit_transactions"

    id = Column(Integer, primary_key=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("user_accounts.id"), nullable=True)  # Who made the transaction

    # Transaction details
    amount = Column(Float, nullable=False)
    balance_after = Column(Float, nullable=False)
    operation = Column(String(50), nullable=False)  # purchase, search, refund, transfer

    # Reference
    search_id = Column(Integer, nullable=True)
    description = Column(String(500), nullable=True)
    metadata_json = Column(Text, nullable=True)

    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    team = relationship("Team")
    user = relationship("UserAccount")

    def __repr__(self):
        return f"<TeamCreditTransaction(team={self.team_id}, amount={self.amount})>"
