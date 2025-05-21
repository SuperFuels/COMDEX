# backend/schemas/product.py

from pydantic import BaseModel, EmailStr

class ProductBase(BaseModel):
    title: str
    origin_country: str
    category: str
    description: str
    image_url: str
    price_per_kg: float
    change_pct: float = 0.0
    rating: float = 0.0

class ProductCreate(ProductBase):
    """
    Used for incoming POST/PUT bodies.
    """
    pass

class ProductOut(ProductBase):
    """
    What we return in GET/POST responses.
    """
    id: int
    owner_email: EmailStr
    owner_wallet_address: str    # ← newly added field

    class Config:
        # Pydantic V2 replaces orm_mode with from_attributes
        from_attributes = True

