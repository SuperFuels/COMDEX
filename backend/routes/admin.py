# File: backend/routes/admin.py

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import Base, engine, get_db
from backend.models.user import User
from backend.models.product import Product
from backend.models.deal import Deal
from backend.schemas.user import UserOut
from backend.schemas.product import ProductOut
from backend.schemas.deal import DealOut
from backend.utils.auth import get_current_user

router = APIRouter(
    prefix="/admin",   # all endpoints now under /api/admin/*
    tags=["Admin"],
)

def _ensure_admin(user: User):
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized",
        )

@router.get("/users", response_model=List[UserOut], summary="Get All Users")
def get_all_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_admin(current_user)
    return db.query(User).all()

@router.get("/products", response_model=List[ProductOut], summary="Get All Products")
def get_all_products(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_admin(current_user)
    return db.query(Product).all()

@router.get("/deals", response_model=List[DealOut], summary="Get All Deals")
def get_all_deals(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _ensure_admin(current_user)
    return db.query(Deal).all()