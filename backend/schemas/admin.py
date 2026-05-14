from pydantic import BaseModel
from typing import List
from datetime import datetime

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

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

