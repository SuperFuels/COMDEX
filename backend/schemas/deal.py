# backend/schemas/deal.py

from pydantic import BaseModel
from datetime import datetime

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

class DealCreate(BaseModel):
    product_id: int
    quantity_kg: float

class DealStatusUpdate(BaseModel):
    status: str

    class Config:
        # Pydantic V2: 'orm_mode' has been renamed to 'from_attributes'
        from_attributes = True

class DealOut(BaseModel):
    id: int
    buyer_email: str
    supplier_email: str
    product_title: str
    quantity_kg: float
    total_price: float
    status: str
    created_at: datetime
    # on-chain address of the supplier
    supplier_wallet_address: str

    class Config:
        from_attributes = True

