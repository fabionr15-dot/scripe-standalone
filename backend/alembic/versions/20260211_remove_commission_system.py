"""Remove commission system from referrals

Revision ID: 003_remove_commission
Revises: 002_referral
Create Date: 2026-02-11

Removes:
- referral_commissions table
- commission_earned column from referral_codes
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "003_remove_commission"
down_revision: Union[str, None] = "002_referral"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove commission tracking tables and columns."""

    # Drop referral_commissions table
    op.drop_table("referral_commissions")

    # Remove commission_earned column from referral_codes
    op.drop_column("referral_codes", "commission_earned")


def downgrade() -> None:
    """Restore commission tracking tables and columns."""

    # Add commission_earned column back to referral_codes
    op.add_column(
        "referral_codes",
        sa.Column("commission_earned", sa.Float(), nullable=True, default=0.0)
    )

    # Recreate referral_commissions table
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
