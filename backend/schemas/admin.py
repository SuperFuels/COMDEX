from pydantic import BaseModel
from typing import List
from datetime import datetime

class UserOut(BaseModel):
    id: int
    name: str
    email: str
    role: str

    class Config:
        from_attributes = True

class ProductOut(BaseModel):
    id: int
    title: str
    origin_country: str
    price_per_kg: float
    category: str
    description: str
    image_url: str
    owner_email: str

    class Config:
        from_attributes = True

class DealOut(BaseModel):
    id: int
    buyer_email: str
    supplier_email: str
    product_title: str
    quantity_kg: int
    total_price: float
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

