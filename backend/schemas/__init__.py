# backend/schemas/__init__.py

from schemas.base import *
from schemas.product import ProductCreate, ProductOut
from schemas.deal import DealCreate, DealOut, DealStatusUpdate
from schemas.contract import ContractCreate, ContractOut
from schemas.user import UserOut, WalletUpdate
# …etc, listing whatever you need to re-export