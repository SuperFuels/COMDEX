# backend/models/__init__.py

"""
Package‐level import of all SQLAlchemy models.
"""

# Import each model so that SQLAlchemy will register its table on Base.metadata
from .user     import User
from .deal     import Deal
from .product  import Product
from .contract import Contract
# ...and any other models you have:
# from .admin import Admin
# from .order import Order

__all__ = [
    "User",
    "Deal",
    "Product",
    "Contract",
    # "Admin", "Order", etc.
]