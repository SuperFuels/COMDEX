from pydantic import BaseModel
from typing import Optional

class DealCreate(BaseModel):
    buyer_email: str
    supplier_email: str
    product_title: str
    quantity_kg: float
    total_price: float

    class Config:
        orm_mode = True  # This ensures compatibility with SQLAlchemy models

class DealOut(DealCreate):
    id: int
    status: Optional[str] = "Pending"

    class Config:
        from_attributes = True  # This is for Pydantic v2+ for compatibility with SQLAlchemy models

