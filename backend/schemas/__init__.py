# backend/schemas/__init__.py

from backend.schemas.base import *
from backend.schemas.product import ProductCreate, ProductOut
from backend.schemas.deal import DealCreate, DealOut, DealStatusUpdate
from backend.schemas.contract import ContractCreate, ContractOut
from backend.schemas.user import UserOut, WalletUpdate
# ...etc, listing whatever you need to re-export