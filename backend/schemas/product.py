# backend/schemas/product.py

from pydantic import BaseModel, EmailStr
from typing import Optional

class ProductBase(BaseModel):
    title: str
    origin_country: str
    category: str
    description: str
    image_url: str
    price_per_kg: float

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
    owner_email: EmailStr   # ← include the supplier’s email

    class Config:
        orm_mode = True

