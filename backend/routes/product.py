from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models.product import Product
from schemas.product import ProductCreate, ProductOut
from typing import List
from utils.auth import get_current_user

router = APIRouter()

@router.get("/", response_model=List[ProductOut])
def list_products(db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    return db.query(Product).filter(Product.owner_email == current_user).all()

@router.post("/create", response_model=ProductOut)
def create_product(product: ProductCreate, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    new_product = Product(
        title=product.title,
        origin_country=product.origin_country,
        category=product.category,
        description=product.description,
        image_url=product.image_url,
        price_per_kg=product.price_per_kg,
        owner_email=current_user
    )
    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    return new_product

