from fastapi import APIRouter, Depends, HTTPException, Form, File, UploadFile
from sqlalchemy.orm import Session
from database import get_db
from models.product import Product
from models.user import User
from utils.auth import get_current_user
from schemas import ProductOut, ProductCreate
from typing import List
import shutil
import os

router = APIRouter()

# ✅ Get all products by current user (used for /dashboard view)
@router.get("/me", response_model=List[ProductOut])
def get_my_products(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    print("🔑 Current user:", current_user.email)
    return db.query(Product).filter(Product.owner_email == current_user.email).all()

# ✅ Get ALL products (public view / homepage)
@router.get("/", response_model=List[ProductOut])
def get_all_products(db: Session = Depends(get_db)):
    return db.query(Product).all()

# ✅ Create Product with image upload
@router.post("/create", response_model=ProductOut)
def create_product(
    title: str = Form(...),
    origin_country: str = Form(...),
    category: str = Form(...),
    description: str = Form(...),
    price_per_kg: float = Form(...),
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    image_dir = "uploaded_images"
    os.makedirs(image_dir, exist_ok=True)
    image_path = os.path.join(image_dir, image.filename)
    
    with open(image_path, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)

    image_url = f"/uploaded_images/{image.filename}"

    new_product = Product(
        title=title,
        origin_country=origin_country,
        category=category,
        description=description,
        price_per_kg=price_per_kg,
        image_url=image_url,
        owner_email=current_user.email
    )
    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    return new_product

# ✅ Update Product
@router.put("/{product_id}", response_model=ProductOut)
def update_product(
    product_id: int,
    updated_data: ProductCreate,
    db: Session = Depends(get_db),  
    current_user: User = Depends(get_current_user)
):
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.owner_email == current_user.email
    ).first()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    for key, value in updated_data.dict().items():
        setattr(product, key, value)

    db.commit()
    db.refresh(product)
    return product

# ✅ Delete Product
@router.delete("/{product_id}")
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.owner_email == current_user.email
    ).first()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    db.delete(product)
    db.commit()
    return {"detail": "Product deleted successfully"}

