from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models.product import Product
from models.user import User
from utils.auth import get_current_user
from schemas import ProductCreate, ProductOut
from typing import List

router = APIRouter(
    prefix="/products",
    tags=["Products"]
)

# ✅ Get all products by current user
@router.get("/", response_model=List[ProductOut])
def get_products(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Query all products where the owner's email matches the current user's email
    return db.query(Product).filter(Product.owner_email == current_user.email).all()

# ✅ Create Product
@router.post("/create", response_model=ProductOut)
def create_product(
    product: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Create a new product instance, and associate it with the current user
    new_product = Product(**product.dict(), owner_email=current_user.email)

    db.add(new_product)
    db.commit()
    db.refresh(new_product)

    # Return the newly created product
    return new_product

# ✅ Update Product
@router.put("/{product_id}", response_model=ProductOut)
def update_product(
    product_id: int,
    updated_data: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Fetch the product by its ID and ensure it belongs to the current user
    product = db.query(Product).filter(Product.id == product_id, Product.owner_email == current_user.email).first()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Update the product's attributes based on the provided data
    for key, value in updated_data.dict().items():
        setattr(product, key, value)

    # Commit the changes to the database
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
    # Fetch the product by its ID and ensure it belongs to the current user
    product = db.query(Product).filter(Product.id == product_id, Product.owner_email == current_user.email).first()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Delete the product from the database
    db.delete(product)
    db.commit()
    
    return {"detail": "Product deleted successfully"}

