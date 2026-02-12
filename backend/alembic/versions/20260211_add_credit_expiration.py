"""Add expires_at to credit_transactions

Revision ID: 004_credit_expiration
Revises: 003_remove_commission
Create Date: 2026-02-11

Adds expiration support for credits:
- Bonus credits expire after 12 months
- Purchased credits never expire
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "004_credit_expiration"
down_revision: Union[str, None] = "003_remove_commission"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add expires_at column to credit_transactions."""
    op.add_column(
        "credit_transactions",
        sa.Column("expires_at", sa.DateTime(), nullable=True)
    )
    # Create index for efficient expiration queries
    op.create_index(
        "ix_credit_transactions_expires_at",
        "credit_transactions",
        ["expires_at"],
        unique=False
    )


def downgrade() -> None:
    """Remove expires_at column."""
    op.drop_index("ix_credit_transactions_expires_at", table_name="credit_transactions")
    op.drop_column("credit_transactions", "expires_at")
