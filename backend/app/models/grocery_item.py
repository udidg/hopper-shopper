"""GroceryItem model – an item on the active grocery list."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base


class GroceryItem(Base):
    __tablename__ = "grocery_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    list_id: Mapped[int] = mapped_column(
        ForeignKey("grocery_lists.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )  # Store section label, e.g. "Produce", "Dairy"
    description: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )  # Additional info, e.g. "buy the green one"
    is_scratched: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    preferred_store: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_observed_price: Mapped[float | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    added_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    grocery_list = relationship("GroceryList", back_populates="items")

    def __repr__(self) -> str:
        return f"<GroceryItem(id={self.id}, name={self.name}, scratched={self.is_scratched})>"
