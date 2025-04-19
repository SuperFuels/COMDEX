from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models import User, Product, Deal
from database import get_db
from utils.auth import get_current_user
from schemas.admin import UserOut, ProductOut, DealOut
from typing import List

# ✅ Admin Router
router = APIRouter(
    prefix="/admin",
    tags=["Admin"]
)

# ✅ Admin: Get all users
@router.get("/users", response_model=List[UserOut])
def get_all_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    return db.query(User).all()

# ✅ Admin: Get all products
@router.get("/products", response_model=List[ProductOut])
def get_all_products(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    return db.query(Product).all()

# ✅ Admin: Get all deals
@router.get("/deals", response_model=List[DealOut])
def get_all_deals(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    return db.query(Deal).all()

