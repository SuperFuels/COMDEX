# backend/routes/products.py
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..utils.auth import get_current_user
from ..models.product import Product
from ..schemas.product import ProductOut, ProductCreate

router = APIRouter(
    prefix="/products",
    tags=["Products"]
)
logger = logging.getLogger(__name__)


@router.get("/me", response_model=List[ProductOut])
def get_my_products(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Private: List products owned by the current user.
    """
    products = db.query(Product).filter(Product.owner_id == current_user.id).all()
    for p in products:
        p.owner_wallet_address = current_user.wallet_address or ""
    return products


@router.get("/", response_model=List[ProductOut])
def get_all_products(db: Session = Depends(get_db)):
    """
    Public: List all products.
    """
    products = db.query(Product).all()
    for p in products:
        owner = db.query(User).get(p.owner_id)
        p.owner_wallet_address = owner.wallet_address or "" if owner else ""
    return products

# ... rest unchanged
