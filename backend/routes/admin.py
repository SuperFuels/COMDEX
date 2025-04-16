from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models import User, Product, Deal
from database import get_db
from utils.auth import get_current_user

router = APIRouter()

# Admin: Get all users
@router.get("/users")
def get_users(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Not authorized")
    users = db.query(User).all()
    return users

# Admin: Get all products
@router.get("/products")
def get_products(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Not authorized")
    products = db.query(Product).all()
    return products

# Admin: Get all deals
@router.get("/deals")
def get_deals(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Not authorized")
    deals = db.query(Deal).all()
    return deals

