"""SQLAlchemy models package."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    pass


# Import all models so Alembic can detect them
from app.models.user import User  # noqa: E402, F401
from app.models.grocery_list import GroceryList  # noqa: E402, F401
from app.models.list_member import ListMember  # noqa: E402, F401
from app.models.item_dictionary import ItemDictionary  # noqa: E402, F401
from app.models.grocery_item import GroceryItem  # noqa: E402, F401
from app.models.global_item import GlobalItem  # noqa: E402, F401
