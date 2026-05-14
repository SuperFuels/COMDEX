import os
import uuid
import logging
import shutil
from typing import List, Optional

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    UploadFile,
    File,
    Form,
)
from sqlalchemy.orm import Session

from backend.database import Base, engine, get_db
from backend.utils.auth import get_current_user
from backend.models.product import Product
from backend.models.user import User
from backend.schemas.product import ProductOut, ProductUpdate  # <-- fixed import to absolute

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

router = APIRouter(
    prefix="/products",
    tags=["Products"],
)
logger = logging.getLogger(__name__)

# ensure upload directory exists
UPLOAD_DIR = "uploaded_images"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.get("/me", response_model=List[ProductOut])
def get_my_products(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    GET /api/products/me
    List all products owned by the current supplier.
    """
    if current_user.role != "supplier":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only suppliers can view their products",
        )
    prods = (
        db
        .query(Product)
        .filter(Product.owner_email == current_user.email)
        .all()
    )
    for p in prods:
        p.owner_wallet_address = current_user.wallet_address or ""
    return prods


@router.get("", response_model=List[ProductOut])
def get_all_products(db: Session = Depends(get_db)):
    """
    GET /api/products
    Public: list all products.
    """
    prods = db.query(Product).all()
    for p in prods:
        owner = (
            db
            .query(User)
            .filter(User.email == p.owner_email)
            .first()
        )
        p.owner_wallet_address = owner.wallet_address if owner and owner.wallet_address else ""
    return prods


@router.post(
    "",
    response_model=ProductOut,
    status_code=status.HTTP_201_CREATED,
)
def create_product(
    title: str = Form(...),
    description: Optional[str] = Form(None),
    price_per_kg: float = Form(...),
    origin_country: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    image: UploadFile = File(...),

    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    POST /api/products
    Create a new product (supplier only).
    Expects multipart/form-data:
      - title, description, price_per_kg, origin_country, category
      - image file
    """
    if current_user.role != "supplier":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only suppliers can create products",
        )

    # 1) Save uploaded image
    ext = os.path.splitext(image.filename)[1]
    unique_name = f"{uuid.uuid4().hex}{ext}"
    dest_path = os.path.join(UPLOAD_DIR, unique_name)
    with open(dest_path, "wb") as f:
        shutil.copyfileobj(image.file, f)

    # 2) Create Product record
    product = Product(
        title=title,
        description=description,
        price_per_kg=price_per_kg,
        origin_country=origin_country,
        category=category,
        image_url=f"/{UPLOAD_DIR}/{unique_name}",
        owner_email=current_user.email,
    )
    db.add(product)
    db.commit()
    db.refresh(product)

    # 3) Attach owner wallet before returning
    product.owner_wallet_address = current_user.wallet_address or ""
    return product


@router.put("/{product_id}", response_model=ProductOut)
def update_product(
    product_id: int,
    payload: ProductUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    PUT /api/products/{product_id}
    Update an existing product (supplier only).
    """
    product = (
        db
        .query(Product)
        .filter_by(id=product_id, owner_email=current_user.email)
        .first()
    )
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    for field, value in payload.dict(exclude_unset=True).items():
        setattr(product, field, value)

    db.commit()
    db.refresh(product)
    product.owner_wallet_address = current_user.wallet_address or ""
    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    DELETE /api/products/{product_id}
    Remove a product (supplier only), deleting its image file too.
    """
    product = (
        db
        .query(Product)
        .filter_by(id=product_id, owner_email=current_user.email)
        .first()
    )
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    # remove image file
    try:
        filepath = product.image_url.lstrip("/")
        if os.path.exists(filepath):
            os.remove(filepath)
    except Exception:
        logger.warning(
            f"Failed to delete image file for product {product_id}",
            exc_info=True,
        )

    db.delete(product)
    db.commit()
    return None