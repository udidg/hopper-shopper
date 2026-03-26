"""Add default_detail column to item_history.

Revision ID: 002_add_detail
Revises: 001_initial_bot
Create Date: 2026-03-26
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002_add_detail"
down_revision: Union[str, None] = "001_initial_bot"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if "item_history" in inspector.get_table_names():
        existing_cols = {c["name"] for c in inspector.get_columns("item_history")}
        if "default_detail" not in existing_cols:
            op.add_column(
                "item_history",
                sa.Column("default_detail", sa.String(500), nullable=True),
            )


def downgrade() -> None:
    op.drop_column("item_history", "default_detail")
