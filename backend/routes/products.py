# backend/routes/products.py

import os
import shutil
from typing import List

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    Form,
    File,
    UploadFile,
)
from sqlalchemy.orm import Session

from database import get_db
from utils.auth import get_current_user

from models.product import Product
from schemas.product import ProductOut, ProductCreate
from models.user import User

router = APIRouter(tags=["Products"])


#
# ─── AUTHENTICATED ENDPOINTS ────────────────────
#

@router.get("/me", response_model=List[ProductOut])
def get_my_products(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Private: GET /products/me
    """
    return (
        db.query(Product)
          .filter(Product.owner_email == current_user.email)
          .all()
    )


#
# ─── PUBLIC ENDPOINTS ──────────────────────────
#

@router.get("/", response_model=List[ProductOut])
def get_all_products(db: Session = Depends(get_db)):
    """
    Public: GET /products
    """
    return db.query(Product).all()


@router.get("/search", response_model=List[ProductOut])
def search_products(query: str, db: Session = Depends(get_db)):
    """
    Public: GET /products/search?query=…
    """
    return (
        db.query(Product)
          .filter(
               (Product.title.ilike(f"%{query}%")) |
               (Product.category.ilike(f"%{query}%"))
          )
          .all()
    )


@router.get("/{product_id}", response_model=ProductOut)
def get_product_by_id(
    product_id: int,
    db: Session = Depends(get_db),
):
    """
    Public: GET /products/{product_id}
    """
    product = db.query(Product).get(product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    return product


#
# ─── CREATE / UPDATE / DELETE ────────────────────
#

@router.post("/", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
def create_product_json(
    payload: ProductCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Private: POST /products  (application/json)
    """
    new_product = Product(**payload.dict(), owner_email=current_user.email)
    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    return new_product


@router.post("/create", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
def create_product_with_upload(
    title: str = Form(...),
    origin_country: str = Form(...),
    category: str = Form(...),
    description: str = Form(...),
    price_per_kg: float = Form(...),
    image: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Private: POST /products/create  (multipart/form-data)
    """
    os.makedirs("uploaded_images", exist_ok=True)
    dest = os.path.join("uploaded_images", image.filename)
    with open(dest, "wb") as buf:
        shutil.copyfileobj(image.file, buf)

    new_product = Product(
        title=title,
        origin_country=origin_country,
        category=category,
        description=description,
        price_per_kg=price_per_kg,
        image_url=f"/uploaded_images/{image.filename}",
        owner_email=current_user.email,
    )
    db.add(new_product)
    db.commit()
    db.refresh(new_product)
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

