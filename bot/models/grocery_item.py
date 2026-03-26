"""GroceryItem model — an item on the active grocery list."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.models import Base


class GroceryItem(Base):
    __tablename__ = "grocery_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    list_id: Mapped[int] = mapped_column(
        ForeignKey("grocery_lists.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # e.g. "2", "500"
    unit: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # e.g. "קילו", "גרם", "ליטר"
    brand: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )  # e.g. "תנובה", "עמק"
    category: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )  # Hebrew department name, e.g. "מוצרי חלב"
    description: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )
    is_done: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    price: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    added_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    grocery_list = relationship("GroceryList", back_populates="items")

    def __repr__(self) -> str:
        return f"<GroceryItem(id={self.id}, name={self.name}, done={self.is_done})>"
