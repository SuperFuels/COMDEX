from fastapi import APIRouter, Depends, HTTPException, Form, File, UploadFile
from sqlalchemy.orm import Session
from typing import List
import os
import shutil

from database import get_db
from utils.auth import get_current_user
from models.product import Product
from schemas.product import ProductOut, ProductCreate
from models.user import User

router = APIRouter(tags=["Products"])


#
# ─── PUBLIC ENDPOINTS ──────────────────────────
#

@router.get("", response_model=List[ProductOut])
@router.get("/", response_model=List[ProductOut])
def get_all_products(db: Session = Depends(get_db)):
    """
    Public: fetch every product in the marketplace (GET /products and GET /products/).
    """
    return db.query(Product).all()


@router.get("/search", response_model=List[ProductOut])
def search_products(query: str, db: Session = Depends(get_db)):
    """
    Public: search by title or category via GET /products/search?query=…
    """
    return (
        db.query(Product)
        .filter(
            (Product.title.ilike(f"%{query}%")) |
            (Product.category.ilike(f"%{query}%"))
        )
        .all()
    )


#
# ─── AUTHENTICATED ENDPOINTS ────────────────────
#

@router.get("/me", response_model=List[ProductOut])
def get_my_products(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Private: fetch only the products you own (GET /products/me).
    """
    return (
        db.query(Product)
        .filter(Product.owner_email == current_user.email)
        .all()
    )


@router.get("/{product_id}", response_model=ProductOut)
def get_product_by_id(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Private: fetch one of your own products by ID (GET /products/{product_id}).
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
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.post("", response_model=ProductOut)
@router.post("/", response_model=ProductOut)
def create_product_json(
    product: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Private: create via JSON body (POST /products and POST /products/).
    """
    new = Product(**product.dict(), owner_email=current_user.email)
    db.add(new)
    db.commit()
    db.refresh(new)
    return new


@router.post("/create", response_model=ProductOut)
def create_product_with_upload(
    title: str = Form(...),
    origin_country: str = Form(...),
    category: str = Form(...),
    description: str = Form(...),
    price_per_kg: float = Form(...),
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Private: create with an image file upload (POST /products/create).
    """
    image_dir = "uploaded_images"
    os.makedirs(image_dir, exist_ok=True)

    dest = os.path.join(image_dir, image.filename)
    with open(dest, "wb") as buf:
        shutil.copyfileobj(image.file, buf)

    new = Product(
        title=title,
        origin_country=origin_country,
        category=category,
        description=description,
        price_per_kg=price_per_kg,
        image_url=f"/uploaded_images/{image.filename}",
        owner_email=current_user.email,
    )
    db.add(new)
    db.commit()
    db.refresh(new)
    return new


@router.put("/{product_id}", response_model=ProductOut)
def update_product(
    product_id: int,
    updated: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Private: update one of your products (PUT /products/{product_id}).
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
        raise HTTPException(status_code=404, detail="Product not found")
    for k, v in updated.dict().items():
        setattr(product, k, v)
    db.commit()
    db.refresh(product)
    return product


@router.delete("/{product_id}")
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Private: delete one of your products (DELETE /products/{product_id}).
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
        raise HTTPException(status_code=404, detail="Product not found")
    db.delete(product)
    db.commit()
    return {"detail": "Product deleted successfully"}

