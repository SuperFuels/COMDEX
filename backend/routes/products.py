from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from models import Product, User
from schemas import ProductOut
from database import get_db
from auth import get_current_user

router = APIRouter()

@router.get("/products/me", response_model=List[ProductOut])
def get_my_products(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Product).filter(Product.owner_id == current_user.id).all()

