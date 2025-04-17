from database import Base  # Import Base from database.py
from .user import User    # Import User model
from .deal import Deal    # Import Deal model
from .product import Product  # Import Product model

# Make sure to initialize your models here so they are included in the metadata
# when performing autogenerate migrations using Alembic

