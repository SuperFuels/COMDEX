# backend/models/__init__.py

from database import Base  # Import Base from database.py

# Import all your model classes so they register with Base.metadata
from models.user     import User
from models.deal     import Deal
from models.product  import Product
from models.contract import Contract

# …and any other models you have, for example:
# from models.admin    import Admin
# from models.order    import Order

# This ensures that when you run Base.metadata.create_all() or autogenerate
# migrations with Alembic, all models are included in the metadata.
