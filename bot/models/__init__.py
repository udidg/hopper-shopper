"""SQLAlchemy models for the Hopper Shopper bot."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Import all models so Alembic can discover them
from bot.models.user import User  # noqa: E402, F401
from bot.models.grocery_list import GroceryList  # noqa: E402, F401
from bot.models.grocery_item import GroceryItem  # noqa: E402, F401
from bot.models.item_history import ItemHistory  # noqa: E402, F401
