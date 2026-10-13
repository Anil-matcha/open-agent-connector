"""Initial database schema baseline

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-10-13 10:40:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0001_initial_schema'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    # 1. connections
    if "connections" not in existing_tables:
        op.create_table(
            "connections",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("service", sa.String(64), nullable=False, index=True),
            sa.Column("connection_name", sa.String(64), nullable=False, server_default="default"),
            sa.Column("auth_type", sa.String(32), nullable=False),
            sa.Column("encrypted_value", sa.Text(), nullable=False, server_default=""),
            sa.Column("account_id", sa.String(128), nullable=True),
            sa.Column("display_name", sa.String(128), nullable=True),
            sa.Column("granted_scopes", sa.Text(), nullable=True),
            sa.Column("status", sa.String(32), nullable=False, server_default="active"),
            sa.Column("status_message", sa.Text(), nullable=True),
            sa.Column("last_validated_at", sa.String(32), nullable=True),
            sa.Column("expires_at", sa.String(32), nullable=True),
            sa.Column("created_at", sa.String(32)),
            sa.Column("updated_at", sa.String(32)),
        )
        op.create_index("idx_service_connection", "connections", ["service", "connection_name"], unique=True)

    # 2. oauth_client_configs
    if "oauth_client_configs" not in existing_tables:
        op.create_table(
            "oauth_client_configs",
            sa.Column("service", sa.String(64), primary_key=True),
            sa.Column("encrypted_value", sa.Text(), nullable=False),
            sa.Column("updated_at", sa.String(32)),
        )

    # 3. oauth_states
    if "oauth_states" not in existing_tables:
        op.create_table(
            "oauth_states",
            sa.Column("state", sa.String(64), primary_key=True),
            sa.Column("service", sa.String(64), nullable=False),
            sa.Column("connection_name", sa.String(64), nullable=False, server_default="default"),
            sa.Column("code_verifier", sa.String(128), nullable=True),
            sa.Column("return_uri", sa.String(512), nullable=True),
            sa.Column("created_at", sa.String(32)),
            sa.Column("expires_at", sa.String(32), nullable=False),
        )

    # 4. runtime_tokens
    if "runtime_tokens" not in existing_tables:
        op.create_table(
            "runtime_tokens",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("name", sa.String(64), nullable=False),
            sa.Column("token_hash", sa.String(64), unique=True, nullable=False, index=True),
            sa.Column("allowed_actions", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("blocked_actions", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("allowed_proxies", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("allowed_connections", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("revoked_at", sa.String(32), nullable=True),
            sa.Column("created_at", sa.String(32)),
            sa.Column("last_used_at", sa.String(32), nullable=True),
        )

    # 5. runs
    if "runs" not in existing_tables:
        op.create_table(
            "runs",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("action_id", sa.String(128), nullable=False, index=True),
            sa.Column("service", sa.String(64), nullable=False, index=True),
            sa.Column("caller", sa.String(16), nullable=False, server_default="http"),
            sa.Column("connection_id", sa.String(36), nullable=True),
            sa.Column("ok", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("status_code", sa.Integer(), nullable=False, server_default="200"),
            sa.Column("duration_ms", sa.Float(), nullable=False, server_default="0.0"),
            sa.Column("input_summary", sa.Text(), nullable=True),
            sa.Column("output_summary", sa.Text(), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("started_at", sa.String(32)),
            sa.Column("completed_at", sa.String(32)),
        )

    # 6. action_idempotency
    if "action_idempotency" not in existing_tables:
        op.create_table(
            "action_idempotency",
            sa.Column("key_hash", sa.String(64), primary_key=True),
            sa.Column("payload_hash", sa.String(64), nullable=True),
            sa.Column("action_id", sa.String(128), nullable=False),
            sa.Column("status", sa.String(32), nullable=False),
            sa.Column("response_status", sa.Integer(), nullable=True),
            sa.Column("response_payload", sa.Text(), nullable=True),
            sa.Column("created_at", sa.String(32)),
            sa.Column("expires_at", sa.String(32), nullable=False),
        )

def downgrade() -> None:
    op.drop_table("action_idempotency")
    op.drop_table("runs")
    op.drop_table("runtime_tokens")
    op.drop_table("oauth_states")
    op.drop_table("oauth_client_configs")
    op.drop_table("connections")
