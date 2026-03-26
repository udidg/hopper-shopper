"""Add unique constraints for data integrity.

- Partial unique index on grocery_lists (chat_id) WHERE is_active = true
  → Prevents duplicate active lists per chat (race condition fix)
- Unique index on item_history (chat_id, lower(name))
  → Prevents duplicate history entries per chat+item (upsert race fix)

Also deduplicates any existing data before adding constraints.

Revision ID: 004_unique_constraints
Revises: 003_add_qty_brand
Create Date: 2026-03-26
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "004_unique_constraints"
down_revision: Union[str, None] = "003_add_qty_brand"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    existing_indexes = {
        idx["name"] for idx in inspector.get_indexes("grocery_lists")
    }

    # ── 1. Deduplicate active grocery lists (keep oldest per chat) ──
    if "uq_grocery_lists_chat_active" not in existing_indexes:
        # Remove duplicate active lists — keep the one with the lowest id
        conn.execute(sa.text("""
            DELETE FROM grocery_lists gl
            WHERE gl.is_active = true
              AND gl.id NOT IN (
                  SELECT MIN(id)
                  FROM grocery_lists
                  WHERE is_active = true
                  GROUP BY chat_id
              )
        """))

        # Create partial unique index
        op.create_index(
            "uq_grocery_lists_chat_active",
            "grocery_lists",
            ["chat_id"],
            unique=True,
            postgresql_where=sa.text("is_active = true"),
        )

    # ── 2. Deduplicate item history (keep the one with highest times_added) ──
    if "item_history" in inspector.get_table_names():
        history_indexes = {
            idx["name"] for idx in inspector.get_indexes("item_history")
        }

        if "uq_item_history_chat_name" not in history_indexes:
            # Merge duplicates: keep the entry with the highest times_added,
            # sum up times_added from duplicates
            conn.execute(sa.text("""
                WITH duplicates AS (
                    SELECT chat_id, lower(name) AS lname,
                           MIN(id) AS keep_id,
                           SUM(times_added) AS total_added
                    FROM item_history
                    GROUP BY chat_id, lower(name)
                    HAVING COUNT(*) > 1
                )
                UPDATE item_history
                SET times_added = d.total_added
                FROM duplicates d
                WHERE item_history.id = d.keep_id
            """))

            conn.execute(sa.text("""
                DELETE FROM item_history ih
                WHERE EXISTS (
                    SELECT 1 FROM item_history ih2
                    WHERE ih2.chat_id = ih.chat_id
                      AND lower(ih2.name) = lower(ih.name)
                      AND ih2.id < ih.id
                )
            """))

            # Create unique index on (chat_id, lower(name))
            op.create_index(
                "uq_item_history_chat_name",
                "item_history",
                ["chat_id", sa.text("lower(name)")],
                unique=True,
            )


def downgrade() -> None:
    op.drop_index("uq_item_history_chat_name", table_name="item_history")
    op.drop_index("uq_grocery_lists_chat_active", table_name="grocery_lists")
