"""GlobalItem model – pre-seeded common grocery items for autocomplete."""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class GlobalItem(Base):
    """
    Read-only, pre-seeded table of common grocery items.

    Provides autocomplete suggestions for all users, even new ones
    who haven't built up their own ItemDictionary yet.
    Stores bilingual names (English + Hebrew) and categories.
    """

    __tablename__ = "global_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    name_he: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    category_he: Mapped[str | None] = mapped_column(String(100), nullable=True)

    def __repr__(self) -> str:
        return f"<GlobalItem(id={self.id}, name={self.name}, name_he={self.name_he})>"
