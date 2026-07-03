"""Add developer_accounts and developer_api_keys tables

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-03 00:00:00.000000

Replaces the in-memory BillingService (accounts and API keys vanished on restart)
with durable Postgres tables following the existing async repository pattern.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "developer_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("account_id", sa.String(20), unique=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("balance_usd", sa.Numeric(15, 2), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_dev_accounts_active", "developer_accounts", ["is_active", "created_at"])
    op.create_check_constraint(
        "check_non_negative_balance", "developer_accounts", "balance_usd >= 0"
    )

    op.create_table(
        "developer_api_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("key", sa.String(64), unique=True, nullable=False),
        sa.Column(
            "account_id",
            sa.String(20),
            sa.ForeignKey("developer_accounts.account_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
    )
    op.create_index("idx_dev_api_keys_key", "developer_api_keys", ["key"])
    op.create_index(
        "idx_dev_api_keys_account_active", "developer_api_keys", ["account_id", "is_active"]
    )


def downgrade() -> None:
    op.drop_table("developer_api_keys")
    op.drop_table("developer_accounts")
