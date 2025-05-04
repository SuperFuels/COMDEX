# backend/schemas/deal.py

from pydantic import BaseModel
from datetime import datetime

class DealCreate(BaseModel):
    product_id: int
    quantity_kg: float

class DealOut(BaseModel):
    id: int
    buyer_email: str
    supplier_email: str
    product_title: str
    quantity_kg: float
    total_price: float
    status: str
    created_at: datetime

    class Config:
        orm_mode = True

