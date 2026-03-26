"""Add quantity, unit, brand columns to grocery_items.

Revision ID: 003_add_qty_brand
Revises: 002_add_detail
Create Date: 2026-03-26
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "003_add_qty_brand"
down_revision: Union[str, None] = "002_add_detail"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "grocery_items",
        sa.Column("quantity", sa.String(50), nullable=True),
    )
    op.add_column(
        "grocery_items",
        sa.Column("unit", sa.String(50), nullable=True),
    )
    op.add_column(
        "grocery_items",
        sa.Column("brand", sa.String(100), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("grocery_items", "brand")
    op.drop_column("grocery_items", "unit")
    op.drop_column("grocery_items", "quantity")
