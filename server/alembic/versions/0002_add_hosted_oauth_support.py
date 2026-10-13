"""Add auth_mode column to oauth_states for hosted support

Revision ID: 0002_add_hosted_oauth_support
Revises: 0001_initial_schema
Create Date: 2026-10-13 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0002_add_hosted_oauth_support'
down_revision: Union[str, Sequence[str], None] = '0001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_columns = [c["name"] for c in inspector.get_columns("oauth_states")]
    
    if "auth_mode" not in existing_columns:
        with op.batch_alter_table("oauth_states") as batch_op:
            batch_op.add_column(sa.Column("auth_mode", sa.String(32), nullable=True, server_default="hosted"))

def downgrade() -> None:
    with op.batch_alter_table("oauth_states") as batch_op:
        batch_op.drop_column("auth_mode")
