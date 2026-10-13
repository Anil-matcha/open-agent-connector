"""Add user accounts: users, account_sessions, email_challenges

Revision ID: 0004_add_accounts
Revises: 0003_add_tenant_ownership
Create Date: 2026-10-14 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0004_add_accounts'
down_revision: Union[str, Sequence[str], None] = '0003_add_tenant_ownership'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "users" not in tables:
        op.create_table(
            "users",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("email", sa.String(254), nullable=False),
            sa.Column("password_hash", sa.String(255), nullable=False),
            sa.Column("tenant_id", sa.String(64), nullable=False),
            sa.Column("is_email_verified", sa.Boolean, nullable=False, server_default=sa.false()),
            sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.String(32)),
            sa.Column("last_login_at", sa.String(32)),
            sa.Column("password_changed_at", sa.String(32)),
            sa.UniqueConstraint("email"),
            sa.UniqueConstraint("tenant_id"),
        )
        op.create_index("ix_users_email", "users", ["email"])
    if "account_sessions" not in tables:
        op.create_table(
            "account_sessions",
            sa.Column("token_hash", sa.String(64), primary_key=True),
            sa.Column("user_id", sa.String(36), nullable=False),
            sa.Column("created_at", sa.String(32)),
            sa.Column("expires_at", sa.String(32), nullable=False),
            sa.Column("last_used_at", sa.String(32)),
            sa.Column("revoked", sa.Boolean, nullable=False, server_default=sa.false()),
            sa.Column("user_agent", sa.String(512)),
            sa.Column("ip", sa.String(64)),
        )
        op.create_index("ix_account_sessions_user_id", "account_sessions", ["user_id"])
    if "email_challenges" not in tables:
        op.create_table(
            "email_challenges",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("user_id", sa.String(36), nullable=False),
            sa.Column("purpose", sa.String(32), nullable=False),
            sa.Column("code_hash", sa.String(64), nullable=False),
            sa.Column("attempts", sa.Integer, nullable=False, server_default="0"),
            sa.Column("created_at", sa.String(32)),
            sa.Column("expires_at", sa.String(32), nullable=False),
            sa.Column("consumed_at", sa.String(32)),
        )
        op.create_index("idx_challenge_user_purpose", "email_challenges", ["user_id", "purpose"])


def downgrade() -> None:
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    for table in ("email_challenges", "account_sessions", "users"):
        if table in tables:
            op.drop_table(table)
