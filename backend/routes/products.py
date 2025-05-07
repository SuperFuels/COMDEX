# backend/routes/products.py

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from utils.auth import get_current_user

from models.product import Product
from models.user import User
from schemas.product import ProductOut, ProductCreate

router = APIRouter(tags=["Products"])

logger = logging.getLogger(__name__)


@router.get("/me", response_model=List[ProductOut])
def get_my_products(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Private: GET /products/me
    """
    prods = (
        db.query(Product)
          .filter(Product.owner_email == current_user.email)
          .all()
    )
    for p in prods:
        owner = db.query(User).filter(User.email == p.owner_email).first()
        p.owner_wallet_address = owner.wallet_address or "" if owner else ""
    return prods


@router.get("/", response_model=List[ProductOut])
def get_all_products(db: Session = Depends(get_db)):
    """
    Public: GET /products
    """
    prods = db.query(Product).all()
    for p in prods:
        owner = db.query(User).filter(User.email == p.owner_email).first()
        p.owner_wallet_address = owner.wallet_address or "" if owner else ""
    return prods


@router.get("/search", response_model=List[ProductOut])
def search_products(query: str, db: Session = Depends(get_db)):
    """
    Public: GET /products/search?query=…
    """
    prods = (
        db.query(Product)
          .filter(
            (Product.title.ilike(f"%{query}%")) |
            (Product.category.ilike(f"%{query}%"))
          )
          .all()
    )
    for p in prods:
        owner = db.query(User).filter(User.email == p.owner_email).first()
        p.owner_wallet_address = owner.wallet_address or "" if owner else ""
    return prods


@router.get("/{product_id}", response_model=ProductOut)
def get_product_by_id(
    product_id: int,
    db: Session = Depends(get_db),
):
    """
    Public: GET /products/{product_id}
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    owner = db.query(User).filter(User.email == product.owner_email).first()
    product.owner_wallet_address = owner.wallet_address or "" if owner else ""
    return product


@router.post("/", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
def create_product(
    payload: ProductCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Private: POST /products  (application/json, including image_url)
    """
    new_product = Product(**payload.dict(), owner_email=current_user.email)
    db.add(new_product)
    db.commit()
    db.refresh(new_product)

    # attach on‑chain wallet address
    new_product.owner_wallet_address = current_user.wallet_address or ""
    return new_product


@router.put("/{product_id}", response_model=ProductOut)
def update_product(
    product_id: int,
    payload: ProductCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Private: PUT /products/{product_id}
    """
    product = (
        db.query(Product)
          .filter(
            Product.id == product_id,
            Product.owner_email == current_user.email,
          )
          .first()
    )
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    for field, value in payload.dict().items():
        setattr(product, field, value)
    db.commit()
    db.refresh(product)

    product.owner_wallet_address = current_user.wallet_address or ""
    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Private: DELETE /products/{product_id}
    """
    product = (
        db.query(Product)
          .filter(
            Product.id == product_id,
            Product.owner_email == current_user.email,
          )
          .first()
    )
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    db.delete(product)
    db.commit()
    return

