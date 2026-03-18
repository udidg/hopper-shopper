"""ListMember model – join table between Users and GroceryLists."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base


class ListMember(Base):
    __tablename__ = "list_members"
    __table_args__ = (
        UniqueConstraint("user_id", "list_id", name="uq_user_list"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    list_id: Mapped[int] = mapped_column(
        ForeignKey("grocery_lists.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, default="member"
    )  # "owner" | "member"
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    user = relationship("User", back_populates="memberships")
    grocery_list = relationship("GroceryList", back_populates="members")

    def __repr__(self) -> str:
        return f"<ListMember(user_id={self.user_id}, list_id={self.list_id}, role={self.role})>"
