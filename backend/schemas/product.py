from typing import Optional, List
from pydantic import BaseModel, EmailStr

class ProductBase(BaseModel):
    title: str
    origin_country: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    price_per_kg: float
    change_pct: Optional[float] = 0.0
    rating: Optional[float] = 0.0
    batch_number: Optional[str] = None
    trace_id: Optional[str] = None
    certificate_url: Optional[str] = None
    blockchain_tx_hash: Optional[str] = None

class ProductCreate(ProductBase):
    """
    Schema for creating a new product (POST body).
    """
    pass

class ProductUpdate(BaseModel):
    """
    Schema for updating an existing product (PUT body).
    All fields optional, only set ones will be updated.
    """
    title: Optional[str] = None
    origin_country: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    price_per_kg: Optional[float] = None
    change_pct: Optional[float] = None
    rating: Optional[float] = None
    batch_number: Optional[str] = None
    trace_id: Optional[str] = None
    certificate_url: Optional[str] = None
    blockchain_tx_hash: Optional[str] = None

class ProductOut(ProductBase):
    """
    Schema returned in GET/POST/PUT responses.
    Includes the auto-generated ID and owner info.
    """
    id: int
    owner_email: EmailStr
    owner_wallet_address: str

    class Config:
        from_attributes = True
