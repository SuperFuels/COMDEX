# backend/schemas/user.py

from pydantic import BaseModel, EmailStr
from typing import Optional

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: Optional[str] = "buyer"

class WalletUpdate(BaseModel):
    wallet_address: str

class UserOut(BaseModel):
    id: int
    name: str
    email: str
    role: str
    wallet_address: Optional[str] = None

    class Config:
        from_attributes = True

# ─── NEW ────────────────────────────────────────────────────────────────

class ProfileOut(BaseModel):
    id: int
    name: str
    email: str
    role: str
    wallet_address: Optional[str] = None

    class Config:
        from_attributes = True