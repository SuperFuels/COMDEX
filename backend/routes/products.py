import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..utils.auth import get_current_user
from ..models.product import Product
from ..models.user import User
from ..schemas.product import ProductOut, ProductCreate, ProductUpdate

router = APIRouter(
    prefix="/products",
    tags=["Products"]
)
logger = logging.getLogger(__name__)


@router.get("/me", response_model=List[ProductOut])
def get_my_products(
    current_user: User = Depends(get_current_user),
    db: Session         = Depends(get_db),
):
    """
    Private: List products owned by the current user.
    """
    if current_user.role != "supplier":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only suppliers can view their products"
        )
    products = (
        db
        .query(Product)
        .filter(Product.owner_email == current_user.email)
        .all()
    )
    for p in products:
        p.owner_wallet_address = current_user.wallet_address or ""
    return products


@router.get("/", response_model=List[ProductOut])
def get_all_products(
    db: Session = Depends(get_db)
):
    """
    Public: List all products.
    """
    products = db.query(Product).all()
    for p in products:
        owner = db.query(User).filter(User.email == p.owner_email).first()
        p.owner_wallet_address = owner.wallet_address or "" if owner else ""
    return products


@router.post("/", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
def create_product(
    product_in: ProductCreate,
    current_user: User = Depends(get_current_user),
    db: Session         = Depends(get_db),
):
    """
    Create a new product owned by the current supplier.
    """
    if current_user.role != "supplier":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only suppliers can create products"
        )
    product = Product(**product_in.dict(), owner_email=current_user.email)
    db.add(product)
    db.commit()
    db.refresh(product)
    product.owner_wallet_address = current_user.wallet_address or ""
    return product


@router.put("/{product_id}", response_model=ProductOut)
def update_product(
    product_id: int,
    product_in: ProductUpdate,
    current_user: User = Depends(get_current_user),
    db: Session         = Depends(get_db),
):
    """
    Update an existing product belonging to the current supplier.
    """
    product = db.query(Product).filter_by(id=product_id, owner_email=current_user.email).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    for field, value in product_in.dict(exclude_unset=True).items():
        setattr(product, field, value)
    db.commit()
    db.refresh(product)
    product.owner_wallet_address = current_user.wallet_address or ""
    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: Session         = Depends(get_db),
):
    """
    Delete a product owned by the current supplier.
    """
    product = db.query(Product).filter_by(id=product_id, owner_email=current_user.email).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    db.delete(product)
    db.commit()
    return None
