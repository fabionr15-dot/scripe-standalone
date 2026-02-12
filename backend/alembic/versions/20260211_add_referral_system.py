"""Add referral system tables

Revision ID: 002_referral
Revises: 001_initial
Create Date: 2026-02-11

Adds tables for:
- referral_codes: Unique codes for each user
- referrals: Tracks referrer/referred relationships
- referral_commissions: Commission history for purchases
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "002_referral"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create referral system tables."""

    # Referral codes table
    op.create_table(
        "referral_codes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("clicks", sa.Integer(), nullable=True, default=0),
        sa.Column("conversions", sa.Integer(), nullable=True, default=0),
        sa.Column("credits_earned", sa.Float(), nullable=True, default=0.0),
        sa.Column("commission_earned", sa.Float(), nullable=True, default=0.0),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["user_accounts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_referral_codes_user_id", "referral_codes", ["user_id"], unique=True)
    op.create_index("ix_referral_codes_code", "referral_codes", ["code"], unique=True)

    # Referrals table (tracks relationships)
    op.create_table(
        "referrals",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("referrer_id", sa.Integer(), nullable=False),
        sa.Column("referred_id", sa.Integer(), nullable=False),
        sa.Column("referral_code_id", sa.Integer(), nullable=False),
        sa.Column("signup_bonus_credited", sa.Boolean(), nullable=True, default=False),
        sa.Column("is_active", sa.Boolean(), nullable=True, default=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["referrer_id"], ["user_accounts.id"]),
        sa.ForeignKeyConstraint(["referred_id"], ["user_accounts.id"]),
        sa.ForeignKeyConstraint(["referral_code_id"], ["referral_codes.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_referrals_referrer_id", "referrals", ["referrer_id"], unique=False)
    op.create_index("ix_referrals_referred_id", "referrals", ["referred_id"], unique=True)

    # Referral commissions table (tracks 20% lifetime commission)
    op.create_table(
        "referral_commissions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("referral_id", sa.Integer(), nullable=False),
        sa.Column("referrer_id", sa.Integer(), nullable=False),
        sa.Column("purchase_amount", sa.Float(), nullable=False),
        sa.Column("commission_rate", sa.Float(), nullable=True, default=0.20),
        sa.Column("commission_credits", sa.Float(), nullable=False),
        sa.Column("credited", sa.Boolean(), nullable=True, default=False),
        sa.Column("credit_transaction_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["referral_id"], ["referrals.id"]),
        sa.ForeignKeyConstraint(["referrer_id"], ["user_accounts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_referral_commissions_referral_id", "referral_commissions", ["referral_id"], unique=False)
    op.create_index("ix_referral_commissions_referrer_id", "referral_commissions", ["referrer_id"], unique=False)

    # Add referral tracking columns to user_accounts
    op.add_column("user_accounts", sa.Column("referred_by_id", sa.Integer(), nullable=True))
    op.add_column("user_accounts", sa.Column("referral_code", sa.String(20), nullable=True))
    op.create_foreign_key(
        "fk_user_accounts_referred_by",
        "user_accounts", "user_accounts",
        ["referred_by_id"], ["id"]
    )


def downgrade() -> None:
    """Drop referral system tables."""
    # Remove columns from user_accounts
    op.drop_constraint("fk_user_accounts_referred_by", "user_accounts", type_="foreignkey")
    op.drop_column("user_accounts", "referral_code")
    op.drop_column("user_accounts", "referred_by_id")

    # Drop tables
    op.drop_table("referral_commissions")
    op.drop_table("referrals")
    op.drop_table("referral_codes")
