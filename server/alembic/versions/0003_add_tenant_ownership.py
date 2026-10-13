"""Add tenant_id ownership columns and per-tenant connection uniqueness

Revision ID: 0003_add_tenant_ownership
Revises: 0002_add_hosted_oauth_support
Create Date: 2026-10-14 10:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0003_add_tenant_ownership'
down_revision: Union[str, Sequence[str], None] = '0002_add_hosted_oauth_support'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TENANT_TABLES = ("connections", "oauth_states", "runtime_tokens", "runs", "action_idempotency")


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = set(inspector.get_table_names())

    for table in TENANT_TABLES:
        if table not in tables:
            continue
        columns = {c["name"] for c in inspector.get_columns(table)}
        if "tenant_id" not in columns:
            with op.batch_alter_table(table) as batch_op:
                batch_op.add_column(
                    sa.Column("tenant_id", sa.String(64), nullable=False, server_default="default")
                )
        index_names = {i["name"] for i in sa.inspect(conn).get_indexes(table)}
        if f"ix_{table}_tenant_id" not in index_names:
            op.create_index(f"ix_{table}_tenant_id", table, ["tenant_id"])

    if "connections" in tables:
        index_names = {i["name"] for i in sa.inspect(conn).get_indexes("connections")}
        if "idx_service_connection" in index_names:
            op.drop_index("idx_service_connection", table_name="connections")
        if "idx_tenant_service_connection" not in index_names:
            op.create_index(
                "idx_tenant_service_connection",
                "connections",
                ["tenant_id", "service", "connection_name"],
                unique=True,
            )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = set(inspector.get_table_names())

    if "connections" in tables:
        index_names = {i["name"] for i in inspector.get_indexes("connections")}
        if "idx_tenant_service_connection" in index_names:
            op.drop_index("idx_tenant_service_connection", table_name="connections")
        op.create_index(
            "idx_service_connection", "connections", ["service", "connection_name"], unique=True
        )

    for table in TENANT_TABLES:
        if table not in tables:
            continue
        if f"ix_{table}_tenant_id" in {i["name"] for i in sa.inspect(conn).get_indexes(table)}:
            op.drop_index(f"ix_{table}_tenant_id", table_name=table)
        with op.batch_alter_table(table) as batch_op:
            batch_op.drop_column("tenant_id")
