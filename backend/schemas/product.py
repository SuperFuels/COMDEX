# backend/schemas/product.py

from pydantic import BaseModel, EmailStr

class ProductBase(BaseModel):
    title: str
    origin_country: str
    category: str
    description: str
    image_url: str
    price_per_kg: float
    change_pct: float = 0.0   # new field
    rating: float = 0.0       # new field

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

    class Config:
        orm_mode = True

