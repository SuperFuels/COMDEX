# backend/routes/admin.py

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.user import User
from ..models.product import Product
from ..models.deal import Deal
from ..schemas.admin import UserOut, ProductOut, DealOut
from ..utils.auth import get_current_user

router = APIRouter(tags=["Admin"])  # prefix applied in main.py


@router.get("/users", response_model=List[UserOut], summary="Get All Users")
def get_all_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized",
        )
    return db.query(User).all()


@router.get("/products", response_model=List[ProductOut], summary="Get All Products")
def get_all_products(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized",
        )
    return db.query(Product).all()


@router.get("/deals", response_model=List[DealOut], summary="Get All Deals")
def get_all_deals(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized",
        )
    return db.query(Deal).all()