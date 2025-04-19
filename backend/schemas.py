from pydantic import BaseModel
from typing import Optional

# ✅ For Product creation
class ProductCreate(BaseModel):
    title: str
    origin_country: str
    category: str
    description: str
    image_url: str
    price_per_kg: float

# ✅ For Product responses
class ProductOut(ProductCreate):
    id: int
    owner_email: str

    class Config:
        from_attributes = True  # This replaces `orm_mode = True` in Pydantic v2

