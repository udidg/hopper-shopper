"""Add quantity, unit, brand columns to grocery_items.

Revision ID: 003
Revises: 002
Create Date: 2026-03-26
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


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
