# backend/routes/products.py

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from database import get_db
from utils.auth import get_current_user
from models.product import Product
from models.user import User
from schemas.product import ProductOut, ProductCreate

router = APIRouter(tags=["Products"])
logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/verify")


@router.get("/me", response_model=List[ProductOut])
def get_my_products(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    """
    Private: List products owned by the current user.
    """
    user = get_current_user(token)
    products = db.query(Product).filter(Product.owner_email == user.email).all()
    for p in products:
        # always produce a string
        p.owner_wallet_address = user.wallet_address or ""
    return products


@router.get("/", response_model=List[ProductOut])
def get_all_products(db: Session = Depends(get_db)):
    """
    Public: List all products.
    """
    products = db.query(Product).all()
    for p in products:
        owner = db.query(User).filter(User.email == p.owner_email).first()
        p.owner_wallet_address = (owner.wallet_address or "") if owner else ""
    return products


@router.get("/search", response_model=List[ProductOut])
def search_products(query: str, db: Session = Depends(get_db)):
    """
    Public: Search products by title or category.
    """
    products = (
        db.query(Product)
          .filter(
              Product.title.ilike(f"%{query}%") |
              Product.category.ilike(f"%{query}%")
          )
          .all()
    )
    for p in products:
        owner = db.query(User).filter(User.email == p.owner_email).first()
        p.owner_wallet_address = (owner.wallet_address or "") if owner else ""
    return products


@router.get("/{product_id}", response_model=ProductOut)
def get_product_by_id(product_id: int, db: Session = Depends(get_db)):
    """
    Public: Get a product by its ID.
    """
    p = db.query(Product).filter(Product.id == product_id).first()
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    owner = db.query(User).filter(User.email == p.owner_email).first()
    p.owner_wallet_address = (owner.wallet_address or "") if owner else ""
    return p


@router.post("/", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
def create_product(
    payload: ProductCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Private: Create a new product (authenticated user).
    """
    new_product = Product(**payload.dict(), owner_email=current_user.email)
    db.add(new_product)
    db.commit()
    db.refresh(new_product)

    new_product.owner_wallet_address = current_user.wallet_address or ""
    return new_product


@router.put("/{product_id}", response_model=ProductOut)
def update_product(
    product_id: int,
    payload: ProductCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Private: Update an existing product.
    """
    p = (
        db.query(Product)
          .filter(
              Product.id == product_id,
              Product.owner_email == current_user.email,
          )
          .first()
    )
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    
    for field, value in payload.dict().items():
        setattr(p, field, value)

    db.commit()
    db.refresh(p)

    p.owner_wallet_address = current_user.wallet_address or ""
    return p


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Private: Delete a product.
    """
    p = (
        db.query(Product)
          .filter(
              Product.id == product_id,
              Product.owner_email == current_user.email,
          )
          .first()
    )
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
        
    db.delete(p)
    db.commit()

