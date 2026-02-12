"""Initial database schema

Revision ID: 001_initial
Revises: None
Create Date: 2026-02-11

This migration creates all tables for the initial Scripe schema.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all initial tables."""

    # User accounts table
    op.create_table(
        "user_accounts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("auth_provider", sa.Enum("local", "zitadel", "google", "github", name="authprovider"), nullable=True),
        sa.Column("external_id", sa.String(255), nullable=True),
        sa.Column("password_hash", sa.String(255), nullable=True),
        sa.Column("email_verified", sa.Boolean(), nullable=True, default=False),
        sa.Column("subscription_tier", sa.Enum("free", "pro", "enterprise", name="subscriptiontier"), nullable=True),
        sa.Column("subscription_expires_at", sa.DateTime(), nullable=True),
        sa.Column("credits_balance", sa.Float(), nullable=True, default=0.0),
        sa.Column("credits_used_total", sa.Float(), nullable=True, default=0.0),
        sa.Column("settings_json", sa.Text(), nullable=True),
        sa.Column("default_country", sa.String(2), nullable=True, default="IT"),
        sa.Column("default_language", sa.String(5), nullable=True, default="it"),
        sa.Column("is_active", sa.Boolean(), nullable=True, default=True),
        sa.Column("is_admin", sa.Boolean(), nullable=True, default=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("last_login_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_accounts_email", "user_accounts", ["email"], unique=True)
    op.create_index("ix_user_accounts_external_id", "user_accounts", ["external_id"], unique=False)

    # Credit transactions table
    op.create_table(
        "credit_transactions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("balance_after", sa.Float(), nullable=False),
        sa.Column("operation", sa.String(50), nullable=False),
        sa.Column("search_id", sa.Integer(), nullable=True),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["user_accounts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_credit_transactions_user_id", "credit_transactions", ["user_id"], unique=False)

    # Searches table
    op.create_table(
        "searches",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("query", sa.String(500), nullable=False),
        sa.Column("country", sa.String(10), nullable=True, default="IT"),
        sa.Column("countries_json", sa.Text(), nullable=True),
        sa.Column("regions_json", sa.Text(), nullable=True),
        sa.Column("cities_json", sa.Text(), nullable=True),
        sa.Column("keywords_include_json", sa.Text(), nullable=True),
        sa.Column("keywords_exclude_json", sa.Text(), nullable=True),
        sa.Column("target_count", sa.Integer(), nullable=True, default=100),
        sa.Column("quality_tier", sa.String(20), nullable=True, default="standard"),
        sa.Column("status", sa.String(20), nullable=True, default="pending"),
        sa.Column("total_companies", sa.Integer(), nullable=True, default=0),
        sa.Column("require_phone", sa.Boolean(), nullable=True, default=True),
        sa.Column("require_website", sa.Boolean(), nullable=True, default=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # User searches (many-to-many link)
    op.create_table(
        "user_searches",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("search_id", sa.Integer(), nullable=False),
        sa.Column("credits_spent", sa.Float(), nullable=True, default=0.0),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["user_accounts.id"]),
        sa.ForeignKeyConstraint(["search_id"], ["searches.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_searches_user_id", "user_searches", ["user_id"], unique=False)

    # Saved lists table
    op.create_table(
        "saved_lists",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("companies_json", sa.Text(), nullable=True),
        sa.Column("company_count", sa.Integer(), nullable=True, default=0),
        sa.Column("source_search_id", sa.Integer(), nullable=True),
        sa.Column("is_public", sa.Boolean(), nullable=True, default=False),
        sa.Column("share_token", sa.String(64), nullable=True),
        sa.Column("is_archived", sa.Boolean(), nullable=True, default=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["user_accounts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_saved_lists_user_id", "saved_lists", ["user_id"], unique=False)
    op.create_index("ix_saved_lists_share_token", "saved_lists", ["share_token"], unique=True)

    # Runs table
    op.create_table(
        "runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("search_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=True, default="pending"),
        sa.Column("progress", sa.Float(), nullable=True, default=0.0),
        sa.Column("companies_found", sa.Integer(), nullable=True, default=0),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["search_id"], ["searches.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_runs_search_id", "runs", ["search_id"], unique=False)

    # Companies table
    op.create_table(
        "companies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("search_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("website", sa.String(500), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("alternative_phones_json", sa.Text(), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("address_line", sa.String(500), nullable=True),
        sa.Column("postal_code", sa.String(20), nullable=True),
        sa.Column("city", sa.String(255), nullable=True),
        sa.Column("region", sa.String(255), nullable=True),
        sa.Column("country", sa.String(10), nullable=True),
        sa.Column("category", sa.String(255), nullable=True),
        sa.Column("categories_json", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("quality_score", sa.Float(), nullable=True),
        sa.Column("data_sources_json", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["search_id"], ["searches.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_companies_search_id", "companies", ["search_id"], unique=False)

    # Sources table
    op.create_table(
        "sources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("url", sa.String(1000), nullable=True),
        sa.Column("data_json", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sources_company_id", "sources", ["company_id"], unique=False)

    # API Keys table
    op.create_table(
        "api_keys",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("key_hash", sa.String(255), nullable=False),
        sa.Column("key_prefix", sa.String(10), nullable=False),
        sa.Column("scopes_json", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True, default=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["user_accounts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_api_keys_user_id", "api_keys", ["user_id"], unique=False)
    op.create_index("ix_api_keys_key_prefix", "api_keys", ["key_prefix"], unique=False)

    # Processed webhook events table (for idempotency)
    op.create_table(
        "processed_webhook_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.String(255), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("processed_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_processed_webhook_events_event_id", "processed_webhook_events", ["event_id"], unique=True)


def downgrade() -> None:
    """Drop all tables."""
    op.drop_table("processed_webhook_events")
    op.drop_table("api_keys")
    op.drop_table("sources")
    op.drop_table("companies")
    op.drop_table("runs")
    op.drop_table("saved_lists")
    op.drop_table("user_searches")
    op.drop_table("credit_transactions")
    op.drop_table("searches")
    op.drop_table("user_accounts")

    # Drop enums
    op.execute("DROP TYPE IF EXISTS authprovider")
    op.execute("DROP TYPE IF EXISTS subscriptiontier")
