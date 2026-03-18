"""ItemDictionary model – historical item registry for auto-suggestions."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base


class ItemDictionary(Base):
    __tablename__ = "item_dictionary"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    list_id: Mapped[int | None] = mapped_column(
        ForeignKey("grocery_lists.id", ondelete="SET NULL"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True
    )  # e.g. "Paper Towels - Kirkland"
    default_category: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )  # e.g. "Cleaning", "Produce"
    last_observed_price: Mapped[float | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    preferred_store: Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    user = relationship("User", back_populates="dictionary_items")

    def __repr__(self) -> str:
        return f"<ItemDictionary(id={self.id}, name={self.name})>"
