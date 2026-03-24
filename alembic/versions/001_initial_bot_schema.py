"""Migrate from Mini App schema to Bot schema.

Adapts the existing database:
- Adds chat_id and is_active to grocery_lists
- Renames is_scratched → is_done in grocery_items
- Adds price column to grocery_items
- Creates item_history table
- Drops unused tables: list_members, item_dictionary, global_items

Revision ID: 001_initial_bot
Revises: None
Create Date: 2026-03-24
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001_initial_bot"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Detect if this is a fresh DB or an existing one ──────────
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    if "users" not in existing_tables:
        # ── Fresh database — create everything from scratch ──────
        _create_fresh_schema()
    else:
        # ── Existing database — migrate from old schema ──────────
        _migrate_existing_schema(existing_tables)


def _create_fresh_schema() -> None:
    """Create all tables from scratch (fresh deployment)."""
    # Users
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(255), nullable=True),
        sa.Column("display_name", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("telegram_id"),
    )
    op.create_index("ix_users_telegram_id", "users", ["telegram_id"])

    # Grocery Lists
    op.create_table(
        "grocery_lists",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "name", sa.String(255), nullable=False, server_default="רשימת קניות"
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], ondelete="SET NULL"
        ),
    )
    op.create_index("ix_grocery_lists_chat_id", "grocery_lists", ["chat_id"])

    # Grocery Items
    op.create_table(
        "grocery_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("list_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("is_done", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("price", sa.Numeric(10, 2), nullable=True),
        sa.Column("added_by", sa.Integer(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["list_id"], ["grocery_lists.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["added_by"], ["users.id"], ondelete="SET NULL"
        ),
    )
    op.create_index("ix_grocery_items_list_id", "grocery_items", ["list_id"])

    # Item History
    _create_item_history_table()


def _migrate_existing_schema(existing_tables: list[str]) -> None:
    """Migrate from the old Mini App schema to the new Bot schema."""

    # ── 1. Modify grocery_lists: add chat_id, is_active; drop invite_code ──
    existing_cols = {
        c["name"]
        for c in sa.inspect(op.get_bind()).get_columns("grocery_lists")
    }

    if "chat_id" not in existing_cols:
        op.add_column(
            "grocery_lists",
            sa.Column("chat_id", sa.BigInteger(), nullable=True),
        )
        # Set a default chat_id for existing lists (will need manual update)
        op.execute("UPDATE grocery_lists SET chat_id = id WHERE chat_id IS NULL")
        op.alter_column("grocery_lists", "chat_id", nullable=False)
        op.create_index("ix_grocery_lists_chat_id", "grocery_lists", ["chat_id"])

    if "is_active" not in existing_cols:
        op.add_column(
            "grocery_lists",
            sa.Column(
                "is_active", sa.Boolean(), nullable=False, server_default="true"
            ),
        )

    if "created_by" not in existing_cols:
        op.add_column(
            "grocery_lists",
            sa.Column("created_by", sa.Integer(), nullable=True),
        )

    if "invite_code" in existing_cols:
        # Drop unique constraint on invite_code first
        try:
            op.drop_constraint(
                "grocery_lists_invite_code_key", "grocery_lists", type_="unique"
            )
        except Exception:
            pass  # Constraint might not exist or have a different name
        op.drop_column("grocery_lists", "invite_code")

    # ── 2. Modify grocery_items: rename is_scratched → is_done, add price ──
    item_cols = {
        c["name"]
        for c in sa.inspect(op.get_bind()).get_columns("grocery_items")
    }

    if "is_scratched" in item_cols and "is_done" not in item_cols:
        op.alter_column(
            "grocery_items", "is_scratched", new_column_name="is_done"
        )

    if "price" not in item_cols:
        op.add_column(
            "grocery_items",
            sa.Column("price", sa.Numeric(10, 2), nullable=True),
        )

    # Copy last_observed_price to price if it exists
    if "last_observed_price" in item_cols:
        op.execute(
            "UPDATE grocery_items SET price = last_observed_price WHERE price IS NULL AND last_observed_price IS NOT NULL"
        )
        op.drop_column("grocery_items", "last_observed_price")

    if "preferred_store" in item_cols:
        op.drop_column("grocery_items", "preferred_store")

    if "updated_at" in item_cols:
        op.drop_column("grocery_items", "updated_at")

    # ── 3. Create item_history table ──
    if "item_history" not in existing_tables:
        _create_item_history_table()

    # ── 4. Drop unused tables ──
    for table in ["list_members", "item_dictionary", "global_items"]:
        if table in existing_tables:
            op.drop_table(table)

    # ── 5. Drop alembic_version from old backend if it exists ──
    # (We're starting fresh with our own migration chain)


def _create_item_history_table() -> None:
    """Create the item_history table."""
    op.create_table(
        "item_history",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("default_category", sa.String(100), nullable=True),
        sa.Column("last_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("times_added", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "last_used",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_item_history_chat_id", "item_history", ["chat_id"])


def downgrade() -> None:
    op.drop_table("item_history")
    # Note: downgrade doesn't restore the old schema — it's a one-way migration
