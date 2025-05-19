# backend/models/__init__.py

from database import Base  # Import Base from database.py
from models.user import User      # Import User model
from models.deal import Deal      # Import Deal model
from models.product import Product  # Import Product model

# Make sure to initialize your models here so they are included in the metadata
# when performing autogenerate migrations using Alembic

