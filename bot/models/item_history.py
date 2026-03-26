"""ItemHistory model — tracks historical items per chat for auto-suggestions."""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from bot.models import Base


class ItemHistory(Base):
    __tablename__ = "item_history"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    default_category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    default_detail: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )  # Saved brand/detail, e.g. "של דוד משה"
    last_price: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    times_added: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    last_used: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<ItemHistory(id={self.id}, name={self.name}, detail={self.default_detail})>"
