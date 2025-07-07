# backend/schemas.py

from pydantic import BaseModel, EmailStr

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

# ─── User / Auth Schemas ─────────────────────────────
class UserCreate(BaseModel):
    name:     str
    email:    EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type:   str = "bearer"


# ─── Product Schemas ──────────────────────────────────
class ProductCreate(BaseModel):
    title:          str
    origin_country: str
    category:       str
    description:    str
    image_url:      str
    price_per_kg:   float

class ProductOut(ProductCreate):
    id:          int
    owner_email: EmailStr

    model_config = {
        "from_attributes": True,  # Pydantic v2 replacement for orm_mode
    }

