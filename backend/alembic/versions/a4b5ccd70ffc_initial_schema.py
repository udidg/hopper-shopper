"""Initial schema – stub for existing database tables.

This migration was originally run on the production database.
The file is recreated as a stub so Alembic can resolve the revision chain.
All tables already exist in the database; this migration is a no-op.

Revision ID: a4b5ccd70ffc
Revises:
Create Date: 2026-03-16

"""
from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "a4b5ccd70ffc"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Tables already exist in the database.
    # This is a stub migration to maintain the revision chain.
    pass


def downgrade() -> None:
    # Not safe to drop existing tables.
    pass
