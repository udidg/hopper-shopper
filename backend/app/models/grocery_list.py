"""GroceryList model – represents a household / shared list."""

import secrets
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base


def _generate_invite_code() -> str:
    """Generate a short, URL-safe invite code."""
    return secrets.token_urlsafe(8)


class GroceryList(Base):
    __tablename__ = "grocery_lists"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    invite_code: Mapped[str] = mapped_column(
        String(32), unique=True, nullable=False, default=_generate_invite_code
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    members = relationship("ListMember", back_populates="grocery_list", lazy="selectin")
    items = relationship(
        "GroceryItem",
        back_populates="grocery_list",
        lazy="selectin",
        order_by="GroceryItem.sort_order",
    )

    def __repr__(self) -> str:
        return f"<GroceryList(id={self.id}, name={self.name})>"
