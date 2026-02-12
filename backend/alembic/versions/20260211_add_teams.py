"""Add team accounts

Revision ID: 005_teams
Revises: 004_credit_expiration
Create Date: 2026-02-11

Adds team collaboration features:
- Teams table
- Team members with roles
- Team credit transactions
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "005_teams"
down_revision: Union[str, None] = "004_credit_expiration"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create team tables."""

    # Teams table
    op.create_table(
        "teams",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("credits_balance", sa.Float(), default=0.0),
        sa.Column("credits_used_total", sa.Float(), default=0.0),
        sa.Column("max_members", sa.Integer(), default=5),
        sa.Column("subscription_tier", sa.String(50), default="team_basic"),
        sa.Column("subscription_expires_at", sa.DateTime(), nullable=True),
        sa.Column("settings_json", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["owner_id"], ["user_accounts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_teams_slug", "teams", ["slug"], unique=True)

    # Team members table
    op.create_table(
        "team_members",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("role", sa.String(20), default="member"),
        sa.Column("invited_by_id", sa.Integer(), nullable=True),
        sa.Column("invitation_token", sa.String(64), nullable=True),
        sa.Column("invitation_email", sa.String(255), nullable=True),
        sa.Column("accepted_at", sa.DateTime(), nullable=True),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["user_accounts.id"]),
        sa.ForeignKeyConstraint(["invited_by_id"], ["user_accounts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_team_members_team_id", "team_members", ["team_id"])
    op.create_index("ix_team_members_user_id", "team_members", ["user_id"])
    op.create_index("ix_team_members_invitation_token", "team_members", ["invitation_token"], unique=True)

    # Team credit transactions
    op.create_table(
        "team_credit_transactions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("balance_after", sa.Float(), nullable=False),
        sa.Column("operation", sa.String(50), nullable=False),
        sa.Column("search_id", sa.Integer(), nullable=True),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["user_accounts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_team_credit_transactions_team_id", "team_credit_transactions", ["team_id"])


def downgrade() -> None:
    """Drop team tables."""
    op.drop_table("team_credit_transactions")
    op.drop_table("team_members")
    op.drop_table("teams")
