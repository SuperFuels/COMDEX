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

# For STF authentication in stub
from jose import jwt

router = APIRouter(tags=["Products"])
logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/verify")

# ─── DEV STUB: /products/me returns empty list to avoid 401 ─────────────────
@router.get("/me", response_model=List[ProductOut])
def get_my_products_stub(token: str = Depends(oauth2_scheme)):
    """
    DEV STUB: Always return an empty list (or canned data) for /products/me to
    prevent 401 during development.
    """
    # Optionally, return some mock products for frontend testing:
    # return [ProductOut(id=0, title="Mock", category="Cat", origin_country="US", price_per_kg=0.0, image_url="/placeholder.jpg", owner_wallet_address="")]  
    return []

# ─── Public: GET /products ──────────────────────────────────────────────────
@router.get("/", response_model=List[ProductOut])
def get_all_products(db: Session = Depends(get_db)):
    """
    Public: List all products
    """
    prods = db.query(Product).all()
    for p in prods:
        owner = db.query(User).filter(User.email == p.owner_email).first()
        p.owner_wallet_address = owner.wallet_address or "" if owner else ""
    return prods

# ─── Public: GET /products/search?query=… ─────────────────────────────────
@router.get("/search", response_model=List[ProductOut])
def search_products(query: str, db: Session = Depends(get_db)):
    """
    Public: Search products by title or category
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

# ─── Public: GET /products/{id} ────────────────────────────────────────────
@router.get("/{product_id}", response_model=ProductOut)
def get_product_by_id(
    product_id: int,
    db: Session = Depends(get_db),
):
    """
    Public: Get a product by its ID
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

# ─── Private: POST /products ────────────────────────────────────────────────
@router.post("/", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
def create_product(
    payload: ProductCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Private: Create a new product (authenticated user)
    """
    new_product = Product(**payload.dict(), owner_email=current_user.email)
    db.add(new_product)
    db.commit()
    db.refresh(new_product)

    # attach owner wallet address
    new_product.owner_wallet_address = current_user.wallet_address or ""
    return new_product

# ─── Private: PUT /products/{id} ───────────────────────────────────────────
@router.put("/{product_id}", response_model=ProductOut)
def update_product(
    product_id: int,
    payload: ProductCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Private: Update an existing product
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

# ─── Private: DELETE /products/{id} ────────────────────────────────────────
@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Private: Delete a product
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
