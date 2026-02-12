"""Add billing system

Revision ID: 006_billing
Revises: 005_teams
Create Date: 2026-02-12

Adds billing infrastructure:
- Company fields to user_accounts
- Billing addresses table
- Invoices table
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "006_billing"
down_revision: Union[str, None] = "005_teams"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add billing tables and user fields."""

    # Add company/billing fields to user_accounts
    op.add_column("user_accounts", sa.Column("company_name", sa.String(255), nullable=True))
    op.add_column("user_accounts", sa.Column("vat_id", sa.String(50), nullable=True))
    op.add_column("user_accounts", sa.Column("tax_exempt", sa.Boolean(), server_default="false", nullable=False))
    op.add_column("user_accounts", sa.Column("billing_email", sa.String(255), nullable=True))

    # Billing addresses table
    op.create_table(
        "billing_addresses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("street_address", sa.String(255), nullable=False),
        sa.Column("street_address_2", sa.String(255), nullable=True),
        sa.Column("city", sa.String(100), nullable=False),
        sa.Column("state_province", sa.String(100), nullable=True),
        sa.Column("postal_code", sa.String(20), nullable=False),
        sa.Column("country", sa.String(2), nullable=False),
        sa.Column("is_primary", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user_accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_billing_addresses_user_id", "billing_addresses", ["user_id"])

    # Invoices table
    op.create_table(
        "invoices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("invoice_number", sa.String(50), nullable=False),
        sa.Column("invoice_date", sa.DateTime(), nullable=False),
        sa.Column("due_date", sa.DateTime(), nullable=True),
        sa.Column("subtotal", sa.Numeric(10, 2), nullable=False),
        sa.Column("tax_rate", sa.Numeric(5, 2), server_default="0", nullable=False),
        sa.Column("tax_amount", sa.Numeric(10, 2), server_default="0", nullable=False),
        sa.Column("total", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency", sa.String(3), server_default="EUR", nullable=False),
        sa.Column("status", sa.String(20), server_default="paid", nullable=False),
        sa.Column("stripe_invoice_id", sa.String(255), nullable=True),
        sa.Column("stripe_payment_intent_id", sa.String(255), nullable=True),
        sa.Column("stripe_checkout_session_id", sa.String(255), nullable=True),
        sa.Column("items_json", sa.Text(), nullable=True),
        sa.Column("billing_address_snapshot", sa.Text(), nullable=True),
        sa.Column("customer_snapshot", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user_accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_invoices_user_id", "invoices", ["user_id"])
    op.create_index("ix_invoices_invoice_number", "invoices", ["invoice_number"], unique=True)


def downgrade() -> None:
    """Remove billing tables and user fields."""

    # Drop tables
    op.drop_index("ix_invoices_invoice_number", table_name="invoices")
    op.drop_index("ix_invoices_user_id", table_name="invoices")
    op.drop_table("invoices")

    op.drop_index("ix_billing_addresses_user_id", table_name="billing_addresses")
    op.drop_table("billing_addresses")

    # Remove columns from user_accounts
    op.drop_column("user_accounts", "billing_email")
    op.drop_column("user_accounts", "tax_exempt")
    op.drop_column("user_accounts", "vat_id")
    op.drop_column("user_accounts", "company_name")
